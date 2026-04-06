from typing import Dict, Any, Optional
from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

try:
    from .models import CodeReviewAction, CodeReviewObservation
except (ImportError, ModuleNotFoundError):
    from models import CodeReviewAction, CodeReviewObservation

class CodeReviewEnv(EnvClient[CodeReviewAction, CodeReviewObservation, State]):
    def _step_payload(self, action: CodeReviewAction) -> Dict:
        return {
            "action_type": action.action_type,
            "bug_line": action.bug_line,
            "bug_type": action.bug_type,
            "description": action.description,
            "fixed_code": action.fixed_code,
            "file_path": action.file_path,
        }

    def _parse_result(self, payload: Dict) -> StepResult[CodeReviewObservation]:
        obs_data = payload.get("observation", {})
        observation = CodeReviewObservation(
            content=obs_data.get("content"),
            feedback=obs_data.get("feedback", ""),
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
            metadata=obs_data.get("metadata", {}),
        )
        return StepResult(
            observation=observation,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
