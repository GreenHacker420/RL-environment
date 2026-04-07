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
BENCHMARK = "code_review_env"
TEMPERATURE = 0
MAX_TOKENS = 2200
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


def log_end(success: bool, steps: int, rewards: list[float]) -> None:
    reward_values = ",".join(f"{reward:.2f}" for reward in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} rewards={reward_values}", flush=True)


def require_api_key() -> str:
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN environment variable is required.")
    return HF_TOKEN


def build_system_prompt() -> str:
    return (
        "You are debugging a pull request in an iterative code-review environment. "
        "Return only valid JSON with keys: fixed_code and summary. "
        "fixed_code must be a full code string for single-file tasks or a JSON object "
        "mapping filenames to updated code strings for multi-file tasks."
    )


def build_user_prompt(prompt: str, feedback: str, attempt: int, max_attempts: int) -> str:
    return (
        f"Attempt: {attempt}/{max_attempts}\n"
        f"Feedback from previous submission: {feedback}\n\n"
        f"{prompt}\n\n"
        "Return only JSON."
    )


def extract_json(text: str) -> dict[str, Any]:
    match = JSON_BLOCK_RE.search(text)
    if not match:
        raise ValueError("Model response did not contain a JSON object.")
    return json.loads(match.group(0))


def normalize_action(payload: dict[str, Any]) -> ReviewAction:
    return ReviewAction(
        fixed_code=payload.get("fixed_code", ""),
        summary=str(payload.get("summary", "")),
    )


def get_model_action(
    client: OpenAI,
    prompt: str,
    feedback: str,
    attempt: int,
    max_attempts: int,
    seed: int,
) -> tuple[str, ReviewAction]:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        seed=seed,
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {
                "role": "user",
                "content": build_user_prompt(
                    prompt=prompt,
                    feedback=feedback,
                    attempt=attempt,
                    max_attempts=max_attempts,
                ),
            },
        ],
    )
    content = (response.choices[0].message.content or "").strip()
    payload = extract_json(content)
    return content, normalize_action(payload)


def sanitize_action_for_log(action: ReviewAction) -> str:
    payload = {
        "summary": action.summary,
        "fixed_code_type": "dict" if isinstance(action.fixed_code, dict) else "str",
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
    return [TASKS[index % len(TASKS)] for index in range(episodes)]


def run_inference(url: str, episodes: int, seed: int) -> dict[str, Any]:
    random.seed(seed)
    np.random.seed(seed)

    model_client = OpenAI(base_url=API_BASE_URL, api_key=require_api_key())
    records: list[dict[str, Any]] = []

    for episode_index, task in enumerate(task_schedule(episodes), start=1):
        rewards: list[float] = []
        steps_taken = 0
        score = 0.0
        success = False
        error_message: str | None = None
        model_outputs: list[str] = []
        action_logs: list[str] = []
        last_feedback = ""

        log_start(task=task["id"], env=BENCHMARK, model=MODEL_NAME)
        try:
            env_client = CodeReviewEnvClient(base_url=url).sync()
            with env_client:
                reset_result = env_client.reset(
                    difficulty=task["difficulty"],
                    task_id=task["id"],
                )
                observation = reset_result.observation

                while True:
                    attempt_number = observation.attempt + 1
                    raw_model_response, action = get_model_action(
                        client=model_client,
                        prompt=observation.prompt,
                        feedback=observation.feedback,
                        attempt=attempt_number,
                        max_attempts=observation.max_attempts,
                        seed=seed + episode_index + steps_taken,
                    )
                    model_outputs.append(raw_model_response)
                    action_log = sanitize_action_for_log(action)
                    action_logs.append(action_log)

                    step_result = env_client.step(action)
                    observation = step_result.observation
                    reward = float(step_result.reward or 0.0)
                    rewards.append(reward)
                    steps_taken += 1
                    last_feedback = observation.feedback

                    log_step(
                        step=steps_taken,
                        action=action_log,
                        reward=reward,
                        done=step_result.done,
                        error=None,
                    )

                    if step_result.done:
                        break

                state = env_client.state()
                score = float(state.best_score)
                success = "Solved." in last_feedback
        except Exception as exc:
            error_message = str(exc).replace("\n", " ").strip()
            log_step(
                step=max(1, steps_taken + 1),
                action=action_logs[-1] if action_logs else "null",
                reward=0.0,
                done=True,
                error=error_message,
            )
        finally:
            log_end(success=success, steps=steps_taken, rewards=rewards)

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
                "model_responses": model_outputs,
                "actions": action_logs,
                "final_feedback": last_feedback,
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
