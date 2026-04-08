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
    from .models import ReviewAction, ReviewObservation
    from .tasks import TASKS, render_workspace
except ImportError:
    from client import CodeReviewEnvClient
    from models import ReviewAction, ReviewObservation
    from tasks import TASKS, render_workspace


BENCHMARK = "code_review_env"
TEMPERATURE = 0
MAX_TOKENS = 2600
JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def load_env_file(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            os.environ.setdefault(key, value)


load_env_file()

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")


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
        "You are operating inside a guided Python coding workspace. "
        "You receive a task brief, current workspace files, and deterministic test feedback. "
        "Return only valid JSON with keys `files` and `summary`. "
        "`files` must be an object mapping workspace file paths to the full replacement content for each changed file. "
        "Do not invent new file paths. Do not include markdown fences."
    )


def build_user_prompt(observation: ReviewObservation) -> str:
    failure_block = "None"
    if observation.failure_details:
        failure_block = "\n".join(f"- {detail}" for detail in observation.failure_details)

    return (
        f"Task brief:\n{observation.task_brief}\n\n"
        f"Current workspace:\n{render_workspace(observation.workspace_files)}\n\n"
        f"Latest feedback: {observation.feedback}\n"
        f"Public tests passed: {observation.tests_passed}/{observation.tests_total}\n"
        f"Test runs used: {observation.test_runs_used}/{observation.max_test_runs}\n"
        f"Failure details:\n{failure_block}\n\n"
        "Return only JSON with:\n"
        '{\n'
        '  "files": {"path.py": "full file content"},\n'
        '  "summary": "short note"\n'
        '}\n'
    )


def extract_json(text: str) -> dict[str, Any]:
    match = JSON_BLOCK_RE.search(text)
    if not match:
        raise ValueError("Model response did not contain a JSON object.")
    return json.loads(match.group(0))


def normalize_update_payload(payload: dict[str, Any]) -> ReviewAction:
    files = payload.get("files", {})
    if not isinstance(files, dict):
        files = {}

    normalized_files: dict[str, str] = {}
    for path, content in files.items():
        if isinstance(path, str) and isinstance(content, str):
            normalized_files[path] = content

    return ReviewAction(
        action_type="update_files",
        files=normalized_files,
        summary=str(payload.get("summary", "")),
    )


def get_model_update(
    client: OpenAI,
    observation: ReviewObservation,
    seed: int,
) -> tuple[str, ReviewAction]:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        seed=seed,
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": build_user_prompt(observation)},
        ],
    )
    content = (response.choices[0].message.content or "").strip()
    payload = extract_json(content)
    return content, normalize_update_payload(payload)


def sanitize_action_for_log(action: ReviewAction) -> str:
    payload = {
        "action_type": action.action_type,
        "paths": action.paths,
        "files": sorted(action.files),
        "summary": action.summary,
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
        env_client = CodeReviewEnvClient(base_url=url).sync()

        log_start(task=task["id"], env=BENCHMARK, model=MODEL_NAME)
        try:
            env_client.connect()
            reset_result = env_client.reset(difficulty=task["difficulty"], task_id=task["id"], seed=seed)
            observation = reset_result.observation

            while True:
                raw_model_response, update_action = get_model_update(
                    client=model_client,
                    observation=observation,
                    seed=seed + episode_index + steps_taken,
                )
                model_outputs.append(raw_model_response)

                update_log = sanitize_action_for_log(update_action)
                action_logs.append(update_log)
                update_result = env_client.step(update_action)
                steps_taken += 1
                rewards.append(float(update_result.reward or 0.0))
                log_step(
                    step=steps_taken,
                    action=update_log,
                    reward=float(update_result.reward or 0.0),
                    done=update_result.done,
                    error=None,
                )
                observation = update_result.observation
                last_feedback = observation.feedback
                if update_result.done:
                    success = float(update_result.reward or 0.0) >= 0.999
                    break

                run_action = ReviewAction(action_type="run_tests")
                run_log = sanitize_action_for_log(run_action)
                action_logs.append(run_log)
                test_result = env_client.step(run_action)
                steps_taken += 1
                rewards.append(float(test_result.reward or 0.0))
                log_step(
                    step=steps_taken,
                    action=run_log,
                    reward=float(test_result.reward or 0.0),
                    done=test_result.done,
                    error=None,
                )
                observation = test_result.observation
                last_feedback = observation.feedback
                if test_result.done:
                    success = float(test_result.reward or 0.0) >= 0.999
                    break

            state = env_client.state()
            score = float(state.best_score)
            success = success or score >= 0.999
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
            try:
                env_client.close()
            except Exception:
                pass
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
