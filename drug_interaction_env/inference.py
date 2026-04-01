from __future__ import annotations

import argparse
import json
import os
import random
import re
import statistics
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np

from client import DrugEnvClient
from models import DrugAction, VALID_SEVERITY_LEVELS

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment]


JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
VALID_TRIAGE_LEVELS = ["normal", "caution", "emergency"]
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _safe_action() -> DrugAction:
    return DrugAction(
        severity="moderate",
        explanation="Potential interaction requires review and monitoring.",
        interactions=[],
        triage="caution",
        revised_medications="Review interacting medications and consider holding the highest-risk agent.",
        metadata={"source": "fallback"},
    )


def _extract_json_object(text: str) -> dict[str, Any] | None:
    match = JSON_BLOCK_RE.search(text)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_action_payload(payload: dict[str, Any]) -> DrugAction:
    return DrugAction(
        severity=str(payload.get("severity", "moderate")).lower()
        if str(payload.get("severity", "moderate")).lower() in VALID_SEVERITY_LEVELS
        else "moderate",
        explanation=str(payload.get("explanation", "")),
        interactions=list(payload.get("interactions", []))
        if isinstance(payload.get("interactions", []), list)
        else [],
        triage=str(payload.get("triage", "caution")).lower()
        if str(payload.get("triage", "caution")).lower() in VALID_TRIAGE_LEVELS
        else "caution",
        revised_medications=str(payload.get("revised_medications", "")),
        metadata=dict(payload.get("metadata", {}))
        if isinstance(payload.get("metadata", {}), dict)
        else {},
    )


def _dummy_action(prompt: str, task_type: str, rng: random.Random) -> DrugAction:
    severity = VALID_SEVERITY_LEVELS[rng.randrange(len(VALID_SEVERITY_LEVELS))]
    triage = VALID_TRIAGE_LEVELS[rng.randrange(len(VALID_TRIAGE_LEVELS))]
    if task_type == "medium":
        tokens = re.findall(r"[a-zA-Z][a-zA-Z\-]+", prompt.lower())
        seen: list[str] = []
        for token in tokens:
            if token not in seen and token not in {"patient", "medications", "severity", "identify", "interaction"}:
                seen.append(token)
            if len(seen) >= 4:
                break
        interactions = []
        if len(seen) >= 2:
            interactions.append({"drug1": seen[0], "drug2": seen[1], "severity": severity})
        return DrugAction(
            severity=severity,
            explanation="Potential interaction identified with conservative monitoring.",
            interactions=interactions,
            triage="caution",
            revised_medications="Review list and avoid the highest-risk combination.",
            metadata={"source": "dummy"},
        )
    return DrugAction(
        severity=severity,
        explanation="Potential interaction could affect safety and should be reviewed.",
        interactions=[],
        triage=triage,
        revised_medications="Consider stopping the most suspicious agent pending review.",
        metadata={"source": "dummy"},
    )


def _build_messages(prompt: str, task_type: str) -> list[dict[str, str]]:
    instructions = (
        "You are a clinical drug interaction reasoning agent. "
        "Return only a JSON object with keys: severity, explanation, interactions, triage, revised_medications, metadata. "
        f"Task type: {task_type}. Severity must be one of {VALID_SEVERITY_LEVELS}. "
        "Triage must be one of ['normal', 'caution', 'emergency']. "
        "For medium tasks, include all interacting pairs in interactions."
    )
    return [
        {"role": "system", "content": instructions},
        {"role": "user", "content": prompt},
    ]


def _call_model(
    prompt: str,
    task_type: str,
    model: str,
    base_url: str | None,
    seed: int,
    episode_index: int,
    dummy_rng: random.Random,
) -> tuple[str, DrugAction]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        action = _dummy_action(prompt, task_type, dummy_rng)
        return json.dumps(action.model_dump()), action

    client = OpenAI(api_key=api_key, base_url=base_url)
    extra_headers: dict[str, str] = {}
    referer = os.getenv("OPENROUTER_HTTP_REFERER")
    title = os.getenv("OPENROUTER_X_TITLE")
    if referer:
        extra_headers["HTTP-Referer"] = referer
    if title:
        extra_headers["X-OpenRouter-Title"] = title

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        seed=seed + episode_index,
        messages=_build_messages(prompt, task_type),
        extra_headers=extra_headers or None,
    )
    content = response.choices[0].message.content or ""
    payload = _extract_json_object(content)
    if payload is None:
        fallback = _safe_action()
        fallback.metadata["parse_error"] = True
        fallback.metadata["source"] = "malformed_json"
        return content, fallback
    return content, _normalize_action_payload(payload)


def _summary_table(results: dict[str, Any]) -> str:
    by_difficulty = results["by_difficulty"]
    return "\n".join(
        [
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
    )


async def run_benchmark(
    url: str,
    episodes: int,
    seed: int,
    model: str,
    base_url: str | None = None,
) -> dict[str, Any]:
    random.seed(seed)
    np.random.seed(seed)
    dummy_rng = random.Random(seed)
    episode_records: list[dict[str, Any]] = []

    async with DrugEnvClient(base_url=url) as env:
        for episode_index in range(episodes):
            start = time.perf_counter()
            reset_result = await env.reset()
            observation = reset_result.observation
            raw_response, action = _call_model(
                prompt=observation.prompt,
                task_type=observation.task_type,
                model=model,
                base_url=base_url,
                seed=seed,
                episode_index=episode_index,
                dummy_rng=dummy_rng,
            )
            step_result = await env.step(action)
            duration_s = time.perf_counter() - start
            state = await env.state()

            episode_records.append(
                {
                    "episode_id": state.episode_id,
                    "task_type": observation.task_type,
                    "reward": step_result.reward,
                    "feedback": step_result.observation.feedback,
                    "duration_s": round(duration_s, 4),
                    "model_response": raw_response,
                    "parsed_action": action.model_dump(),
                }
            )

    scores = [record["reward"] for record in episode_records]
    grouped: dict[str, list[float]] = {"easy": [], "medium": [], "hard": []}
    for record in episode_records:
        grouped[record["task_type"]].append(record["reward"])

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "model": model,
        "n_episodes": episodes,
        "mean_score": float(np.mean(scores)) if scores else 0.0,
        "std_score": float(np.std(scores)) if scores else 0.0,
        "p25": float(np.percentile(scores, 25)) if scores else 0.0,
        "p50": float(np.percentile(scores, 50)) if scores else 0.0,
        "p75": float(np.percentile(scores, 75)) if scores else 0.0,
        "safety_violations": sum(
            1 for record in episode_records if "SAFETY VIOLATION" in record["feedback"]
        ),
        "by_difficulty": {
            level: (statistics.mean(values) if values else 0.0)
            for level, values in grouped.items()
        },
        "episodes": episode_records,
    }
    with open("results.json", "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    print(_summary_table(results))
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Drug Interaction Env.")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--episodes", type=int, default=60)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_BASE_URL") or DEFAULT_OPENROUTER_BASE_URL,
    )
    return parser.parse_args()


if __name__ == "__main__":
    import asyncio

    args = parse_args()
    asyncio.run(
        run_benchmark(
            args.url,
            args.episodes,
            args.seed,
            args.model,
            base_url=args.base_url,
        )
    )
