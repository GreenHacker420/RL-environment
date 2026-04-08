from __future__ import annotations

from typing import Any

from openenv.core import EnvClient
from openenv.core.client_types import StepResult

try:
    from .models import ReviewAction, ReviewObservation, ReviewState
except ImportError:
    from models import ReviewAction, ReviewObservation, ReviewState


class CodeReviewEnvClient(
    EnvClient[ReviewAction, ReviewObservation, ReviewState]
):
    """WebSocket client for CodeReviewEnv."""

    def _step_payload(self, action: ReviewAction) -> dict[str, Any]:
        return {
            "action_type": action.action_type,
            "paths": action.paths,
            "files": action.files,
            "summary": action.summary,
            "metadata": action.metadata,
        }

    def _parse_result(self, payload: dict[str, Any]) -> StepResult[ReviewObservation]:
        observation_data = payload.get("observation", {})
        observation = ReviewObservation(
            done=payload.get("done", False),
            solved=observation_data.get("solved", False),
            reward=float(payload.get("reward", 0.0) or 0.0),
            task_brief=observation_data.get("task_brief", ""),
            workspace_files=observation_data.get("workspace_files", {}),
            stdout=observation_data.get("stdout", ""),
            stderr=observation_data.get("stderr", ""),
            exit_code=int(observation_data.get("exit_code", 0)),
            feedback=observation_data.get("feedback", ""),
            failing_tests=list(observation_data.get("failing_tests", [])),
            failure_details=list(observation_data.get("failure_details", [])),
            task_id=observation_data.get("task_id", ""),
            difficulty=observation_data.get("difficulty", ""),
            tests_passed=int(observation_data.get("tests_passed", 0)),
            tests_total=int(observation_data.get("tests_total", 0)),
            test_runs_used=int(observation_data.get("test_runs_used", 0)),
            max_test_runs=int(observation_data.get("max_test_runs", 0)),
            metadata=observation_data.get("metadata", {}),
        )
        return StepResult(
            observation=observation,
            reward=float(payload.get("reward", 0.0) or 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict[str, Any]) -> ReviewState:
        return ReviewState(
            episode_id=payload.get("episode_id", ""),
            step_count=int(payload.get("step_count", 0)),
            difficulty=payload.get("difficulty", "easy"),
            best_score=float(payload.get("best_score", 0.0) or 0.0),
            solved=payload.get("solved", False),
            tests_passed=int(payload.get("tests_passed", 0)),
            tests_total=int(payload.get("tests_total", 0)),
            test_runs_used=int(payload.get("test_runs_used", 0)),
            max_test_runs=int(payload.get("max_test_runs", 0)),
            task_id=payload.get("task_id", ""),
            workspace_manifest=list(payload.get("workspace_manifest", [])),
        )


CodeReviewEnv = CodeReviewEnvClient
