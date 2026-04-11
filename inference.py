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


def strict_unit_interval(value: float, epsilon: float = 5e-3) -> float:
    if value <= epsilon:
        return epsilon
    if value >= 1.0 - epsilon:
        return 1.0 - epsilon
    return value


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


def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    reward_values = ",".join(f"{reward:.2f}" for reward in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={reward_values}",
        flush=True,
    )


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
    loaded_files = render_workspace(observation.workspace_files) if observation.workspace_files else "No files loaded yet."
    manifest_block = "\n".join(f"- {entry}" for entry in observation.workspace_manifest) or "None"
    failure_block = "None"
    if observation.failure_details:
        failure_block = "\n".join(f"- {detail}" for detail in observation.failure_details)

    return (
        f"Task brief:\n{observation.task_brief}\n\n"
        f"Workspace manifest:\n{manifest_block}\n\n"
        f"Loaded workspace files:\n{loaded_files}\n\n"
        f"Latest feedback: {observation.feedback}\n"
        f"Public tests passed: {observation.tests_passed}/{observation.tests_total}\n"
        f"Test runs used: {observation.test_runs_used}/{observation.max_test_runs}\n"
        f"Lint issues: {', '.join(observation.lint_issues) if observation.lint_issues else 'None'}\n"
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


def merge_workspace_cache(
    workspace_cache: dict[str, str],
    observation: ReviewObservation,
) -> ReviewObservation:
    if observation.workspace_files:
        workspace_cache.update(observation.workspace_files)
    return ReviewObservation(
        done=observation.done,
        solved=observation.solved,
        reward=observation.reward,
        task_brief=observation.task_brief,
        workspace_files=dict(workspace_cache),
        workspace_manifest=list(observation.workspace_manifest),
        stdout=observation.stdout,
        stderr=observation.stderr,
        exit_code=observation.exit_code,
        feedback=observation.feedback,
        lint_issues=list(observation.lint_issues),
        failing_tests=list(observation.failing_tests),
        failure_details=list(observation.failure_details),
        task_id=observation.task_id,
        difficulty=observation.difficulty,
        tests_passed=observation.tests_passed,
        tests_total=observation.tests_total,
        test_runs_used=observation.test_runs_used,
        max_test_runs=observation.max_test_runs,
        metadata=observation.metadata,
    )


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
        episode_seed = seed + episode_index - 1
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
            reset_result = env_client.reset(
                difficulty=task["difficulty"],
                task_id=task["id"],
                seed=episode_seed,
            )
            workspace_cache: dict[str, str] = {}
            observation = merge_workspace_cache(workspace_cache, reset_result.observation)

            if observation.workspace_manifest:
                paths = [entry.split(" (", 1)[0] for entry in observation.workspace_manifest]
                read_action = ReviewAction(action_type="read_files", paths=paths, summary="Load workspace files")
                read_log = sanitize_action_for_log(read_action)
                action_logs.append(read_log)
                read_result = env_client.step(read_action)
                steps_taken += 1
                rewards.append(float(read_result.reward or 0.0))
                log_step(
                    step=steps_taken,
                    action=read_log,
                    reward=float(read_result.reward or 0.0),
                    done=read_result.done,
                    error=None,
                )
                observation = merge_workspace_cache(workspace_cache, read_result.observation)
                last_feedback = observation.feedback
                if read_result.done:
                    success = bool(observation.solved)
                    raise RuntimeError("Episode ended during initial read_files step.")

            while True:
                raw_model_response, update_action = get_model_update(
                    client=model_client,
                    observation=observation,
                    seed=episode_seed + steps_taken,
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
                observation = merge_workspace_cache(workspace_cache, update_result.observation)
                last_feedback = observation.feedback
                if update_result.done:
                    success = bool(observation.solved)
                    break

                lint_action = ReviewAction(action_type="run_lint")
                lint_log = sanitize_action_for_log(lint_action)
                action_logs.append(lint_log)
                lint_result = env_client.step(lint_action)
                steps_taken += 1
                rewards.append(float(lint_result.reward or 0.0))
                log_step(
                    step=steps_taken,
                    action=lint_log,
                    reward=float(lint_result.reward or 0.0),
                    done=lint_result.done,
                    error=None,
                )
                observation = merge_workspace_cache(workspace_cache, lint_result.observation)
                last_feedback = observation.feedback
                if lint_result.done:
                    success = bool(observation.solved)
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
                observation = merge_workspace_cache(workspace_cache, test_result.observation)
                last_feedback = observation.feedback
                if test_result.done:
                    success = bool(observation.solved)
                    break

            state = env_client.state()
            score = strict_unit_interval(float(state.best_score))
            success = success or bool(state.solved)
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
            log_end(
                success=success,
                steps=steps_taken,
                score=strict_unit_interval(score),
                rewards=rewards,
            )

        records.append(
            {
                "episode": episode_index,
                "seed": episode_seed,
                "task_id": task["id"],
                "difficulty": task["difficulty"],
                "score": strict_unit_interval(score),
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
    parser.add_argument("--episodes", type=int, default=len(TASKS) * 3)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    run_inference(arguments.url, arguments.episodes, arguments.seed)
