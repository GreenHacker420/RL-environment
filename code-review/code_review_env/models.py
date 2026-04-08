from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


ActionType = str


@dataclass(init=False)
class ReviewAction(Action):
    action_type: ActionType = Field(
        default="read_files",
        description="Workspace action type. One of read_files, update_files, or run_tests.",
    )
    paths: list[str] = Field(
        default_factory=list,
        description="File paths to read from the current workspace.",
    )
    files: dict[str, str] = Field(
        default_factory=dict,
        description="Updated file contents keyed by workspace path.",
    )
    summary: str = Field(
        default="",
        description="Optional short description of what the action is doing.",
    )

    def __init__(
        self,
        action_type: ActionType = "read_files",
        paths: list[str] | None = None,
        files: dict[str, str] | None = None,
        summary: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            action_type=action_type,
            paths=paths or [],
            files=files or {},
            summary=summary,
            metadata=metadata or {},
        )


@dataclass(init=False)
class ReviewObservation(Observation):
    done: bool = Field(default=False, description="Whether the episode is complete.")
    solved: bool = Field(default=False, description="Whether the hidden success condition has been satisfied.")
    reward: float = Field(default=0.0, description="Reward returned by the environment.")
    task_brief: str = Field(default="", description="Short task description for the active workspace.")
    workspace_files: dict[str, str] = Field(
        default_factory=dict,
        description="Visible workspace files returned by the environment.",
    )
    stdout: str = Field(default="", description="Structured stdout-like feedback from the last action.")
    stderr: str = Field(default="", description="Structured stderr-like feedback from the last action.")
    exit_code: int = Field(default=0, description="Exit code for the last action.")
    feedback: str = Field(default="", description="Compact human-readable summary of the last action result.")
    failing_tests: list[str] = Field(
        default_factory=list,
        description="Names of currently failing public or hidden tests from the last run_tests call.",
    )
    failure_details: list[str] = Field(
        default_factory=list,
        description="Small deterministic failure summaries from the last run_tests call.",
    )
    task_id: str = Field(default="", description="Identifier of the current task template.")
    difficulty: str = Field(default="easy", description="Current task difficulty.")
    tests_passed: int = Field(default=0, description="Number of public tests passed by the latest run.")
    tests_total: int = Field(default=0, description="Total number of public tests for the active task.")
    test_runs_used: int = Field(default=0, description="Number of run_tests actions used in this episode.")
    max_test_runs: int = Field(default=0, description="Maximum allowed run_tests actions for this episode.")

    def __init__(
        self,
        done: bool = False,
        solved: bool = False,
        reward: float = 0.0,
        task_brief: str = "",
        workspace_files: dict[str, str] | None = None,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        feedback: str = "",
        failing_tests: list[str] | None = None,
        failure_details: list[str] | None = None,
        task_id: str = "",
        difficulty: str = "easy",
        tests_passed: int = 0,
        tests_total: int = 0,
        test_runs_used: int = 0,
        max_test_runs: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            done=done,
            solved=solved,
            reward=reward,
            task_brief=task_brief,
            workspace_files=workspace_files or {},
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            feedback=feedback,
            failing_tests=failing_tests or [],
            failure_details=failure_details or [],
            task_id=task_id,
            difficulty=difficulty,
            tests_passed=tests_passed,
            tests_total=tests_total,
            test_runs_used=test_runs_used,
            max_test_runs=max_test_runs,
            metadata=metadata or {},
        )


@dataclass(init=False)
class ReviewState(State):
    episode_id: str = Field(default="", description="Current episode identifier.")
    step_count: int = Field(default=0, description="Total number of actions taken in this episode.")
    difficulty: str = Field(default="easy", description="Difficulty of the active workspace.")
    best_score: float = Field(default=0.0, description="Best reward achieved so far in this episode.")
    solved: bool = Field(default=False, description="Whether the episode has been solved.")
    tests_passed: int = Field(default=0, description="Best public test count achieved so far.")
    tests_total: int = Field(default=0, description="Total public test count for the active task.")
    test_runs_used: int = Field(default=0, description="Number of run_tests calls used in the episode.")
    max_test_runs: int = Field(default=0, description="Maximum run_tests calls available in the episode.")
    task_id: str = Field(default="", description="Identifier of the active task template.")
    workspace_manifest: list[str] = Field(
        default_factory=list,
        description="Visible file list for the active workspace.",
    )

    def __init__(
        self,
        episode_id: str = "",
        step_count: int = 0,
        difficulty: str = "easy",
        best_score: float = 0.0,
        solved: bool = False,
        tests_passed: int = 0,
        tests_total: int = 0,
        test_runs_used: int = 0,
        max_test_runs: int = 0,
        task_id: str = "",
        workspace_manifest: list[str] | None = None,
    ) -> None:
        super().__init__(
            episode_id=episode_id,
            step_count=step_count,
            difficulty=difficulty,
            best_score=best_score,
            solved=solved,
            tests_passed=tests_passed,
            tests_total=tests_total,
            test_runs_used=test_runs_used,
            max_test_runs=max_test_runs,
            task_id=task_id,
            workspace_manifest=workspace_manifest or [],
        )
