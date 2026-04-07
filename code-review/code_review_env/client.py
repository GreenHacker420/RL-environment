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
            "bug_line": action.bug_line,
            "bug_type": action.bug_type,
            "description": action.description,
            "fixed_code": action.fixed_code,
            "metadata": action.metadata,
        }

    def _parse_result(self, payload: dict[str, Any]) -> StepResult[ReviewObservation]:
        observation_data = payload.get("observation", {})
        observation = ReviewObservation(
            done=payload.get("done", False),
            reward=float(payload.get("reward", 0.0) or 0.0),
            prompt=observation_data.get("prompt", ""),
            feedback=observation_data.get("feedback", ""),
            task_id=observation_data.get("task_id", ""),
            difficulty=observation_data.get("difficulty", ""),
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
            current_score=float(payload.get("current_score", 0.0) or 0.0),
        )


CodeReviewEnv = CodeReviewEnvClient
