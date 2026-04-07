from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


BugLineType = int | list[dict[str, Any]]
BugTypeType = str | list[str]
FixedCodeType = str | dict[str, str]


@dataclass(init=False)
class ReviewAction(Action):
    bug_line: BugLineType = Field(
        ...,
        description="Bug line for easy tasks or a list of bug reports for medium and hard tasks.",
    )
    bug_type: BugTypeType = Field(
        ...,
        description="Bug type string for easy tasks or a list of bug types for medium and hard tasks.",
    )
    description: str = Field(..., description="Short explanation of the bug or bug summary.")
    fixed_code: FixedCodeType = Field(
        ...,
        description="Corrected code string for easy and medium tasks or a filename-to-code map for hard tasks.",
    )

    def __init__(
        self,
        bug_line: BugLineType,
        bug_type: BugTypeType,
        description: str,
        fixed_code: FixedCodeType,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            bug_line=bug_line,
            bug_type=bug_type,
            description=description,
            fixed_code=fixed_code,
            metadata=metadata or {},
        )


@dataclass(init=False)
class ReviewObservation(Observation):
    done: bool = Field(default=False, description="Whether the episode is complete.")
    reward: float = Field(default=0.0, description="Reward returned by the grader.")
    prompt: str = Field(default="", description="Buggy code shown to the agent.")
    feedback: str = Field(default="", description="Grader or environment feedback.")
    task_id: str = Field(default="", description="Identifier of the current task.")
    difficulty: str = Field(default="easy", description="Current task difficulty.")

    def __init__(
        self,
        done: bool = False,
        reward: float = 0.0,
        prompt: str = "",
        feedback: str = "",
        task_id: str = "",
        difficulty: str = "easy",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            done=done,
            reward=reward,
            prompt=prompt,
            feedback=feedback,
            task_id=task_id,
            difficulty=difficulty,
            metadata=metadata or {},
        )


@dataclass(init=False)
class ReviewState(State):
    episode_id: str = Field(default="", description="Current episode identifier.")
    step_count: int = Field(default=0, description="Number of steps in the current episode.")
    difficulty: str = Field(default="easy", description="Difficulty for the active episode.")
    current_score: float = Field(default=0.0, description="Latest score for the active episode.")

    def __init__(
        self,
        episode_id: str = "",
        step_count: int = 0,
        difficulty: str = "easy",
        current_score: float = 0.0,
    ) -> None:
        super().__init__(
            episode_id=episode_id,
            step_count=step_count,
            difficulty=difficulty,
            current_score=current_score,
        )
