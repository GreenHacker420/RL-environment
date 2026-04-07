from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


FixedCodeType = str | dict[str, str]


@dataclass(init=False)
class ReviewAction(Action):
    fixed_code: FixedCodeType = Field(
        default="",
        description="Revised code submission. Use a string for single-file tasks or a filename-to-code map for multi-file tasks.",
    )
    summary: str = Field(
        default="",
        description="Optional short explanation of the fix strategy or what changed.",
    )

    def __init__(
        self,
        fixed_code: FixedCodeType = "",
        summary: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            fixed_code=fixed_code,
            summary=summary,
            metadata=metadata or {},
        )


@dataclass(init=False)
class ReviewObservation(Observation):
    done: bool = Field(default=False, description="Whether the episode is complete.")
    reward: float = Field(default=0.0, description="Reward returned by the grader.")
    prompt: str = Field(default="", description="Current PR context, code, and task instructions.")
    feedback: str = Field(default="", description="Test feedback from the previous submission.")
    task_id: str = Field(default="", description="Identifier of the current task.")
    difficulty: str = Field(default="easy", description="Current task difficulty.")
    attempt: int = Field(default=0, description="Current attempt number.")
    max_attempts: int = Field(default=0, description="Maximum attempts available in this episode.")
    tests_passed: int = Field(default=0, description="Number of public tests passed by the latest submission.")
    tests_total: int = Field(default=0, description="Total number of public tests for the current task.")

    def __init__(
        self,
        done: bool = False,
        reward: float = 0.0,
        prompt: str = "",
        feedback: str = "",
        task_id: str = "",
        difficulty: str = "easy",
        attempt: int = 0,
        max_attempts: int = 0,
        tests_passed: int = 0,
        tests_total: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            done=done,
            reward=reward,
            prompt=prompt,
            feedback=feedback,
            task_id=task_id,
            difficulty=difficulty,
            attempt=attempt,
            max_attempts=max_attempts,
            tests_passed=tests_passed,
            tests_total=tests_total,
            metadata=metadata or {},
        )


@dataclass(init=False)
class ReviewState(State):
    episode_id: str = Field(default="", description="Current episode identifier.")
    step_count: int = Field(default=0, description="Number of submitted revisions in the current episode.")
    difficulty: str = Field(default="easy", description="Difficulty for the active episode.")
    current_score: float = Field(default=0.0, description="Latest reward observed in the active episode.")
    best_score: float = Field(default=0.0, description="Best reward achieved so far in the active episode.")
    task_id: str = Field(default="", description="Identifier of the active task.")
    max_attempts: int = Field(default=0, description="Maximum revisions available in the active episode.")
    tests_passed: int = Field(default=0, description="Best public test count achieved so far.")
    tests_total: int = Field(default=0, description="Total public tests in the active task.")

    def __init__(
        self,
        episode_id: str = "",
        step_count: int = 0,
        difficulty: str = "easy",
        current_score: float = 0.0,
        best_score: float = 0.0,
        task_id: str = "",
        max_attempts: int = 0,
        tests_passed: int = 0,
        tests_total: int = 0,
    ) -> None:
        super().__init__(
            episode_id=episode_id,
            step_count=step_count,
            difficulty=difficulty,
            current_score=current_score,
            best_score=best_score,
            task_id=task_id,
            max_attempts=max_attempts,
            tests_passed=tests_passed,
            tests_total=tests_total,
        )
