from __future__ import annotations

from dataclasses import asdict
from typing import Any

from core.http_env_client import HTTPEnvClient
from core.types import StepResult

from models import DrugAction, DrugObservation, DrugState


class DrugEnvClient(HTTPEnvClient[DrugAction, DrugObservation]):
    def _step_payload(self, action: DrugAction) -> dict[str, Any]:
        return asdict(action)

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
