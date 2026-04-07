from __future__ import annotations

import argparse
import json
import os
import random
import re
import statistics
from pathlib import Path
from typing import Any

import numpy as np
from openai import OpenAI

try:
    from .client import CodeReviewEnvClient
    from .models import ReviewAction
    from .tasks import TASKS
except ImportError:
    from client import CodeReviewEnvClient
    from models import ReviewAction
    from tasks import TASKS


API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BENCHMARK = "code_review_env"
TEMPERATURE = 0
MAX_TOKENS = 1600
JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: str | None) -> None:
    error_value = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={str(done).lower()} error={error_value}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    reward_values = ",".join(f"{reward:.2f}" for reward in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={reward_values}",
        flush=True,
    )


def require_api_key() -> str:
    api_key = HF_TOKEN or OPENAI_API_KEY
    if not api_key:
        raise RuntimeError("Set HF_TOKEN or OPENAI_API_KEY before running inference.py.")
    return api_key


def build_system_prompt() -> str:
    return (
        "You are solving a code review task. "
        "Return only valid JSON with keys: bug_line, bug_type, description, fixed_code. "
        "For easy tasks use an integer bug_line and a string bug_type. "
        "For medium tasks use bug_line as a list of objects with line, bug_type, description. "
        "For hard tasks use bug_line as a list of objects with file, line, bug_type, description, "
        "and fixed_code as a JSON object mapping filenames to corrected code strings."
    )


def build_user_prompt(task: dict[str, Any], prompt: str) -> str:
    return (
        f"Task ID: {task['id']}\n"
        f"Difficulty: {task['difficulty']}\n"
        "Review the buggy Python code below, identify the bug locations, classify the bug type, "
        "and provide corrected code.\n\n"
        f"{prompt}"
    )


def extract_json(text: str) -> dict[str, Any]:
    match = JSON_BLOCK_RE.search(text)
    if not match:
        raise ValueError("Model response did not contain a JSON object.")
    return json.loads(match.group(0))


def normalize_action(payload: dict[str, Any]) -> ReviewAction:
    bug_line = payload.get("bug_line", -1)
    bug_type = payload.get("bug_type", "")
    description = str(payload.get("description", ""))
    fixed_code = payload.get("fixed_code", "")
    return ReviewAction(
        bug_line=bug_line,
        bug_type=bug_type,
        description=description,
        fixed_code=fixed_code,
    )


def get_model_action(client: OpenAI, task: dict[str, Any], prompt: str, seed: int) -> tuple[str, ReviewAction]:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        seed=seed,
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": build_user_prompt(task, prompt)},
        ],
    )
    content = (response.choices[0].message.content or "").strip()
    payload = extract_json(content)
    return content, normalize_action(payload)


def sanitize_action_for_log(action: ReviewAction) -> str:
    payload = {
        "bug_line": action.bug_line,
        "bug_type": action.bug_type,
        "description": action.description,
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def per_difficulty_breakdown(records: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    breakdown: dict[str, dict[str, float | int]] = {}
    for difficulty in ("easy", "medium", "hard"):
        scores = [item["score"] for item in records if item["difficulty"] == difficulty]
        breakdown[difficulty] = {
            "count": len(scores),
            "mean_score": statistics.mean(scores) if scores else 0.0,
            "std_score": statistics.stdev(scores) if len(scores) > 1 else 0.0,
        }
    return breakdown


def task_schedule(episodes: int) -> list[dict[str, Any]]:
    if episodes <= len(TASKS):
        return TASKS[:episodes]

    scheduled: list[dict[str, Any]] = []
    for index in range(episodes):
        scheduled.append(TASKS[index % len(TASKS)])
    return scheduled


def run_inference(url: str, episodes: int, seed: int) -> dict[str, Any]:
    random.seed(seed)
    np.random.seed(seed)

    model_client = OpenAI(base_url=API_BASE_URL, api_key=require_api_key())
    env_client = CodeReviewEnvClient(base_url=url).sync()
    records: list[dict[str, Any]] = []

    with env_client:
        for episode_index, task in enumerate(task_schedule(episodes), start=1):
            rewards: list[float] = []
            steps_taken = 0
            score = 0.0
            success = False
            error_message: str | None = None
            raw_model_response = ""
            action_log = "null"

            log_start(task=task["id"], env=BENCHMARK, model=MODEL_NAME)
            try:
                reset_result = env_client.reset(
                    difficulty=task["difficulty"],
                    task_id=task["id"],
                )
                prompt = reset_result.observation.prompt

                raw_model_response, action = get_model_action(
                    client=model_client,
                    task=task,
                    prompt=prompt,
                    seed=seed + episode_index,
                )
                action_log = sanitize_action_for_log(action)

                step_result = env_client.step(action)
                reward = float(step_result.reward or 0.0)
                rewards.append(reward)
                steps_taken = 1
                score = max(0.0, min(1.0, reward))
                success = score > 0.0

                log_step(
                    step=1,
                    action=action_log,
                    reward=reward,
                    done=step_result.done,
                    error=None,
                )
            except Exception as exc:
                error_message = str(exc).replace("\n", " ").strip()
                log_step(
                    step=1,
                    action=action_log,
                    reward=0.0,
                    done=True,
                    error=error_message,
                )
            finally:
                log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

            records.append(
                {
                    "episode": episode_index,
                    "task_id": task["id"],
                    "difficulty": task["difficulty"],
                    "score": score,
                    "success": success,
                    "steps": steps_taken,
                    "rewards": rewards,
                    "error": error_message,
                    "model_response": raw_model_response,
                }
            )

    scores = [record["score"] for record in records]
    results = {
        "benchmark": BENCHMARK,
        "model_name": MODEL_NAME,
        "api_base_url": API_BASE_URL,
        "seed": seed,
        "episodes_requested": episodes,
        "mean_score": statistics.mean(scores) if scores else 0.0,
        "std_score": statistics.stdev(scores) if len(scores) > 1 else 0.0,
        "per_difficulty": per_difficulty_breakdown(records),
        "episodes": records,
    }

    Path("results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CodeReviewEnv baseline.")
    parser.add_argument("--url", default="http://localhost:7860")
    parser.add_argument("--episodes", type=int, default=len(TASKS))
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    run_inference(arguments.url, arguments.episodes, arguments.seed)
