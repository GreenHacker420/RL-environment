from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import random
import statistics
import sys
from datetime import datetime, timezone
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from openai import AsyncOpenAI

from graders import grade_easy_task, grade_medium_task
from inference import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_MODEL_TIMEOUT_S,
    build_messages,
    extract_json_object,
    parse_action,
)
from scripts.real_data import (
    build_easy_eval_tasks,
    build_medium_eval_tasks,
    compile_interaction_db,
    load_kagglehub_records,
    load_twosides_records,
)


load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def create_openai_client(base_url: str) -> AsyncOpenAI:
    api_key = require_env("OPENAI_API_KEY")
    headers: dict[str, str] = {}
    referer = os.getenv("OPENROUTER_HTTP_REFERER")
    title = os.getenv("OPENROUTER_X_TITLE")
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-OpenRouter-Title"] = title
    return AsyncOpenAI(api_key=api_key, base_url=base_url, default_headers=headers or None)


async def call_model(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    task_type: str,
    seed: int,
    index: int,
    timeout_s: float,
) -> tuple[str, dict[str, Any]]:
    response = await client.chat.completions.create(
        model=model,
        temperature=0,
        seed=seed + index,
        messages=build_messages(prompt, task_type),
        timeout=timeout_s,
    )
    content = response.choices[0].message.content or ""
    return content, extract_json_object(content)


def summarize(records: list[dict[str, Any]], model: str, source_csv: str) -> dict[str, Any]:
    scores = [record["score"] for record in records]
    grouped: dict[str, list[float]] = {"easy": [], "medium": []}
    for record in records:
        grouped[record["task_type"]].append(record["score"])
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "source_csv": source_csv,
        "n_examples": len(records),
        "mean_score": statistics.mean(scores) if scores else 0.0,
        "std_score": statistics.stdev(scores) if len(scores) > 1 else 0.0,
        "by_task_type": {
            task_type: (statistics.mean(values) if values else 0.0)
            for task_type, values in grouped.items()
        },
        "examples": records,
    }


async def run_real_data_eval(
    source_label: str,
    records_loader: str,
    model: str,
    base_url: str,
    seed: int,
    output_path: str,
    max_rows: int | None,
    easy_limit: int,
    medium_limit: int,
    min_count: float,
    allowed_drugs: set[str] | None,
    model_timeout_s: float,
) -> dict[str, Any]:
    random.seed(seed)
    if records_loader == "csv":
        records = load_twosides_records(source_label, limit=max_rows)
    elif records_loader == "kagglehub":
        dataset_handle, file_path = source_label.split("::", maxsplit=1)
        records = load_kagglehub_records(dataset_handle, file_path=file_path, limit=max_rows)
    else:
        raise RuntimeError(f"Unsupported records loader: {records_loader}")
    compiled_db = compile_interaction_db(records, allowed_drugs=allowed_drugs, min_count=min_count)
    easy_tasks = build_easy_eval_tasks(compiled_db, limit=easy_limit)
    medium_tasks = build_medium_eval_tasks(compiled_db, limit=medium_limit, seed=seed)
    tasks = easy_tasks + medium_tasks

    if not tasks:
        raise RuntimeError("No evaluation tasks could be built from the provided dataset slice.")

    client = create_openai_client(base_url)
    results: list[dict[str, Any]] = []
    for index, task in enumerate(tasks):
        print(f"[real-data {index + 1}/{len(tasks)}] model call ({task.task_type})")
        raw_response, payload = await call_model(
            client=client,
            model=model,
            prompt=task.prompt,
            task_type=task.task_type,
            seed=seed,
            index=index,
            timeout_s=model_timeout_s,
        )
        action = parse_action(payload)
        if task.task_type == "easy":
            score, feedback = grade_easy_task(task, action)
        else:
            score, feedback = grade_medium_task(task, action)
        results.append(
            {
                "task_id": task.id,
                "task_type": task.task_type,
                "score": score,
                "feedback": feedback,
                "input_data": task.input_data,
                "ground_truth": task.ground_truth,
                "parsed_action": action.model_dump(),
                "model_response": raw_response,
            }
        )
        print(f"[real-data {index + 1}/{len(tasks)}] done score={score:.3f}")

    summary = summarize(results, model=model, source_csv=source_label)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    print(json.dumps(summary["by_task_type"], indent=2))
    print(f"mean_score={summary['mean_score']:.3f}")
    print(f"wrote {output_path}")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the model on a real TWOSIDES-style dataset slice.")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--csv", help="Path to a TWOSIDES-style CSV file.")
    source_group.add_argument(
        "--kaggle-dataset",
        help="Kaggle dataset handle, for example mghobashy/drug-drug-interactions.",
    )
    parser.add_argument(
        "--kaggle-file-path",
        default="",
        help="Optional file path inside the Kaggle dataset when using --kaggle-dataset. If omitted, the script auto-selects a likely tabular file.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL") or DEFAULT_BASE_URL)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="real_data_results.json")
    parser.add_argument("--max-rows", type=int, default=200000)
    parser.add_argument("--easy-limit", type=int, default=25)
    parser.add_argument("--medium-limit", type=int, default=10)
    parser.add_argument("--min-count", type=float, default=10.0)
    parser.add_argument("--allowed-drugs", default="")
    parser.add_argument("--model-timeout-s", type=float, default=DEFAULT_MODEL_TIMEOUT_S)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.csv:
        csv_path = Path(args.csv).expanduser().resolve()
        if not csv_path.exists():
            raise RuntimeError(
                "The CSV file was not found. Replace the example placeholder path with the real "
                f"downloaded dataset path. Received: {args.csv!r}. "
                "Example: --csv ~/Downloads/twosides_with_drug_names.csv"
            )
        source_label = str(csv_path)
        records_loader = "csv"
    else:
        source_label = f"{args.kaggle_dataset}::{args.kaggle_file_path}"
        records_loader = "kagglehub"
    allowed_drugs = {
        drug.strip().lower() for drug in args.allowed_drugs.split(",") if drug.strip()
    } or None
    asyncio.run(
        run_real_data_eval(
            source_label=source_label,
            records_loader=records_loader,
            model=args.model,
            base_url=args.base_url,
            seed=args.seed,
            output_path=args.output,
            max_rows=args.max_rows,
            easy_limit=args.easy_limit,
            medium_limit=args.medium_limit,
            min_count=args.min_count,
            allowed_drugs=allowed_drugs,
            model_timeout_s=args.model_timeout_s,
        )
    )
