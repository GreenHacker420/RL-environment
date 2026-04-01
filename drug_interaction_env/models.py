from __future__ import annotations

from typing import Any

from openenv.core.env_server import Action, Observation, State
from pydantic import Field


VALID_SEVERITY_LEVELS = ["none", "mild", "moderate", "severe"]


class DrugAction(Action):
    severity: str = "moderate"
    explanation: str = ""
    interactions: list[dict[str, Any]] = Field(default_factory=list)
    triage: str = "caution"
    revised_medications: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class DrugObservation(Observation):
    prompt: str = ""
    task_id: str = ""
    task_type: str = ""
    feedback: str = ""
    partial_score: float = 0.0
    valid_severity_levels: list[str] = Field(
        default_factory=lambda: list(VALID_SEVERITY_LEVELS)
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class DrugState(State):
    task_type: str = ""
    current_score: float = 0.0
    safety_violations: int = 0

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
