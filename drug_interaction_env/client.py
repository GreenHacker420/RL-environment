from __future__ import annotations

from typing import Any

from openenv.core.client_types import StepResult
from openenv.core.env_client import EnvClient

from models import DrugAction, DrugObservation, DrugState


class DrugEnvClient(EnvClient[DrugAction, DrugObservation, DrugState]):
    def _step_payload(self, action: DrugAction) -> dict[str, Any]:
        return action.model_dump()

    def _parse_result(self, payload: dict[str, Any]) -> StepResult:
        observation_payload = payload.get("observation", payload)
        observation = DrugObservation(**observation_payload)
        return StepResult(
            observation=observation,
            reward=float(payload.get("reward", observation.reward)),
            done=bool(payload.get("done", observation.done)),
        )

    def _parse_state(self, payload: dict[str, Any]) -> DrugState:
        return DrugState(**payload)


if __name__ == "__main__":
    with DrugEnvClient(base_url="http://localhost:8000").sync() as client:
        reset_result = client.reset()
        print(reset_result.observation.prompt)
        action = DrugAction(
            severity="moderate",
            explanation="Possible clinically important interaction requiring monitoring.",
        )
        step_result = client.step(action)
        print(step_result.reward)
        print(step_result.observation.feedback)
