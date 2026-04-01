from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import time
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI
from dotenv import load_dotenv

from client import DrugEnvClient
from models import DrugAction, VALID_SEVERITY_LEVELS


DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
VALID_TRIAGE_LEVELS = ["normal", "caution", "emergency"]
JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def extract_json_object(text: str) -> dict[str, Any]:
    match = JSON_BLOCK_RE.search(text)
    if not match:
        raise ValueError("Model response did not contain a JSON object.")
    return json.loads(match.group(0))


def parse_action(payload: dict[str, Any]) -> DrugAction:
    severity = str(payload.get("severity", "moderate")).lower()
    triage = str(payload.get("triage", "caution")).lower()
    raw_interactions = payload.get("interactions", [])
    interactions = [
        item
        for item in raw_interactions
        if isinstance(item, dict)
    ] if isinstance(raw_interactions, list) else []

    return DrugAction(
        severity=severity if severity in VALID_SEVERITY_LEVELS else "moderate",
        explanation=str(payload.get("explanation", "")),
        interactions=interactions,
        triage=triage if triage in VALID_TRIAGE_LEVELS else "caution",
        revised_medications=str(payload.get("revised_medications", "")),
        metadata=payload.get("metadata", {})
        if isinstance(payload.get("metadata", {}), dict)
        else {},
    )


def build_messages(prompt: str, task_type: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are a clinical drug interaction reasoning agent. "
                "Return only a JSON object with keys: severity, explanation, "
                "interactions, triage, revised_medications, metadata. "
                f"Task type: {task_type}. "
                f"Valid severities: {VALID_SEVERITY_LEVELS}. "
                f"Valid triage: {VALID_TRIAGE_LEVELS}. "
                "interactions must be a JSON array of objects like "
                "[{\"drug1\":\"warfarin\",\"drug2\":\"aspirin\",\"severity\":\"severe\"}]. "
                "Do not return strings inside interactions."
            ),
        },
        {"role": "user", "content": prompt},
    ]


def create_openai_client(base_url: str) -> AsyncOpenAI:
    api_key = require_env("OPENAI_API_KEY")
    headers: dict[str, str] = {}

    referer = os.getenv("OPENROUTER_HTTP_REFERER")
    title = os.getenv("OPENROUTER_X_TITLE")
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-OpenRouter-Title"] = title

    return AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        default_headers=headers or None,
    )


async def call_model(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    task_type: str,
    seed: int,
    episode_index: int,
) -> tuple[str, DrugAction]:
    response = await client.chat.completions.create(
        model=model,
        temperature=0,
        seed=seed + episode_index,
        messages=build_messages(prompt, task_type),
    )
    content = response.choices[0].message.content or ""
    payload = extract_json_object(content)
    return content, parse_action(payload)


def print_summary(results: dict[str, Any]) -> None:
    by_difficulty = results["by_difficulty"]
    lines = [
        "Benchmark Summary",
        "=================",
        f"Model: {results['model']}",
        f"Episodes: {results['n_episodes']}",
        f"Mean score: {results['mean_score']:.3f}",
        f"Std score: {results['std_score']:.3f}",
        f"P25 / P50 / P75: {results['p25']:.3f} / {results['p50']:.3f} / {results['p75']:.3f}",
        f"Safety violations: {results['safety_violations']}",
        f"Easy mean: {by_difficulty.get('easy', 0.0):.3f}",
        f"Medium mean: {by_difficulty.get('medium', 0.0):.3f}",
        f"Hard mean: {by_difficulty.get('hard', 0.0):.3f}",
    ]
    print("\n".join(lines))


async def run_benchmark(url: str, episodes: int, seed: int, model: str, base_url: str) -> dict[str, Any]:
    llm_client = create_openai_client(base_url)
    episode_records: list[dict[str, Any]] = []

    try:
        async with DrugEnvClient(base_url=url) as env:
            for episode_index in range(episodes):
                started_at = time.perf_counter()
                reset_result = await env.reset()
                observation = reset_result.observation

                raw_response, action = await call_model(
                    client=llm_client,
                    model=model,
                    prompt=observation.prompt,
                    task_type=observation.task_type,
                    seed=seed,
                    episode_index=episode_index,
                )

                step_result = await env.step(action)
                state = await env.state()

                episode_records.append(
                    {
                        "episode_id": state.episode_id,
                        "task_type": observation.task_type,
                        "reward": step_result.reward,
                        "feedback": step_result.observation.feedback,
                        "duration_s": round(time.perf_counter() - started_at, 4),
                        "model_response": raw_response,
                        "parsed_action": action.model_dump(),
                    }
                )
    except ConnectionError as exc:
        raise RuntimeError(
            f"Could not connect to environment server at {url}. "
            "Start it first with: uvicorn server.app:app --host 0.0.0.0 --port 8000"
        ) from exc

    scores = [record["reward"] for record in episode_records]
    grouped: dict[str, list[float]] = {"easy": [], "medium": [], "hard": []}
    for record in episode_records:
        grouped[record["task_type"]].append(record["reward"])

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "model": model,
        "n_episodes": episodes,
        "mean_score": statistics.mean(scores) if scores else 0.0,
        "std_score": statistics.stdev(scores) if len(scores) > 1 else 0.0,
        "p25": sorted(scores)[max(0, int(0.25 * (len(scores) - 1)))] if scores else 0.0,
        "p50": statistics.median(scores) if scores else 0.0,
        "p75": sorted(scores)[max(0, int(0.75 * (len(scores) - 1)))] if scores else 0.0,
        "safety_violations": sum(
            1 for record in episode_records if "SAFETY VIOLATION" in record["feedback"]
        ),
        "by_difficulty": {
            difficulty: (statistics.mean(values) if values else 0.0)
            for difficulty, values in grouped.items()
        },
        "episodes": episode_records,
    }

    with open("results.json", "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)

    print_summary(results)
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a real benchmark against Drug Interaction Env.")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL") or DEFAULT_BASE_URL)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        run_benchmark(
            url=args.url,
            episodes=args.episodes,
            seed=args.seed,
            model=args.model,
            base_url=args.base_url,
        )
    )
