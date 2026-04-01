from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from core.env_server import Action, Observation, State


VALID_SEVERITY_LEVELS = ["none", "mild", "moderate", "severe"]


@dataclass
class DrugAction(Action):
    severity: str = "moderate"
    explanation: str = ""
    interactions: list[dict[str, Any]] = field(default_factory=list)
    triage: str = "caution"
    revised_medications: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DrugObservation(Observation):
    done: bool = False
    reward: float = 0.0
    prompt: str = ""
    task_id: str = ""
    task_type: str = ""
    feedback: str = ""
    partial_score: float = 0.0
    valid_severity_levels: list[str] = field(
        default_factory=lambda: list(VALID_SEVERITY_LEVELS)
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DrugState(State):
    episode_id: str | None = None
    step_count: int = 0
    task_type: str = ""
    current_score: float = 0.0
    safety_violations: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
