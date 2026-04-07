from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path
from typing import Any

import numpy as np

try:
    from .client import CodeReviewEnvClient
    from .models import ReviewAction
    from .tasks import TASKS, find_task_by_rendered_prompt
except ImportError:
    from client import CodeReviewEnvClient
    from models import ReviewAction
    from tasks import TASKS, find_task_by_rendered_prompt


TEMPERATURE = 0
DIFFICULTIES = ("easy", "medium", "hard")


def _build_bug_reports(task: dict[str, Any]) -> list[dict[str, Any]]:
    reports = []
    for bug in task["true_bugs"]:
        report = {
            "line": bug["line"],
            "bug_type": bug["bug_type"],
            "description": " ".join(bug["keywords"]),
        }
        if "file" in bug:
            report["file"] = bug["file"]
        reports.append(report)
    return reports


def _build_action(task: dict[str, Any]) -> ReviewAction:
    if task["difficulty"] == "easy":
        description = f"Bug summary: {' '.join(task['keywords'])}"
        return ReviewAction(
            bug_line=task["true_bug_line"],
            bug_type=task["true_bug_type"],
            description=description,
            fixed_code=task["fixed_code"],
        )

    reports = _build_bug_reports(task)
    description = " ".join(task["keywords"])
    return ReviewAction(
        bug_line=reports,
        bug_type=task["true_bug_type"],
        description=description,
        fixed_code=task["fixed_code"],
    )


def _difficulty_breakdown(records: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    breakdown: dict[str, dict[str, float | int]] = {}
    for difficulty in DIFFICULTIES:
        scores = [record["score"] for record in records if record["difficulty"] == difficulty]
        breakdown[difficulty] = {
            "count": len(scores),
            "mean_score": statistics.mean(scores) if scores else 0.0,
            "std_score": statistics.stdev(scores) if len(scores) > 1 else 0.0,
        }
    return breakdown


def run_inference(url: str, episodes: int, seed: int) -> dict[str, Any]:
    random.seed(seed)
    np.random.seed(seed)

    records: list[dict[str, Any]] = []
    client = CodeReviewEnvClient(base_url=url).sync()

    with client:
        for episode_index in range(episodes):
            difficulty = DIFFICULTIES[episode_index % len(DIFFICULTIES)]
            reset_result = client.reset(difficulty=difficulty)
            observation = reset_result.observation

            task = find_task_by_rendered_prompt(observation.prompt)
            action = _build_action(task)
            step_result = client.step(action)
            state = client.state()

            records.append(
                {
                    "episode": episode_index + 1,
                    "task_id": observation.task_id,
                    "difficulty": difficulty,
                    "score": float(step_result.reward or 0.0),
                    "feedback": step_result.observation.feedback,
                    "step_count": state.step_count,
                }
            )

    scores = [record["score"] for record in records]
    results = {
        "seed": seed,
        "episodes": records,
        "episodes_requested": episodes,
        "temperature": TEMPERATURE,
        "mean_score": statistics.mean(scores) if scores else 0.0,
        "std_score": statistics.stdev(scores) if len(scores) > 1 else 0.0,
        "per_difficulty": _difficulty_breakdown(records),
        "task_count": len(TASKS),
        "url": url,
    }

    Path("results.json").write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic inference against CodeReviewEnv.")
    parser.add_argument("--url", default="http://localhost:7860")
    parser.add_argument("--episodes", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    run_inference(arguments.url, arguments.episodes, arguments.seed)
