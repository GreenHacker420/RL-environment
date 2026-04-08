from __future__ import annotations

import random
import sys
from pathlib import Path
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment

try:
    from ..graders import evaluate_workspace, quality_report
    from ..models import ReviewAction, ReviewObservation, ReviewState
    from ..tasks import build_task, build_workspace_summary, get_task_by_id, get_tasks_by_difficulty
except ImportError:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from graders import evaluate_workspace, quality_report
    from models import ReviewAction, ReviewObservation, ReviewState
    from tasks import build_task, build_workspace_summary, get_task_by_id, get_tasks_by_difficulty


def _copy_workspace(files: dict[str, str]) -> dict[str, str]:
    return dict(files)


class CodeReviewEnv(Environment[ReviewAction, ReviewObservation, ReviewState]):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        super().__init__()
        self._task: dict | None = None
        self._workspace: dict[str, str] = {}
        self._done = False
        self._solved = False
        self._last_public_passed = 0
        self._last_failing_tests: list[str] = []
        self._last_failure_details: list[str] = []
        self._state = ReviewState(
            episode_id=str(uuid4()),
            step_count=0,
            difficulty="easy",
            best_score=0.0,
            solved=False,
            tests_passed=0,
            tests_total=0,
            test_runs_used=0,
            max_test_runs=0,
            task_id="",
            workspace_manifest=[],
        )

    def _select_task(self, difficulty: str, seed: int | None, task_id: str | None) -> dict:
        if task_id is not None:
            get_task_by_id(task_id)
            return build_task(task_id, seed=seed)

        candidates = get_tasks_by_difficulty(difficulty)
        if not candidates:
            raise ValueError(f"Unknown difficulty: {difficulty}")

        chooser = random.Random(seed) if seed is not None else random
        descriptor = chooser.choice(candidates)
        return build_task(descriptor["id"], seed=seed)

    def _workspace_view(self, paths: list[str] | None = None) -> dict[str, str]:
        if not paths:
            return _copy_workspace(self._workspace)
        return {path: self._workspace[path] for path in paths if path in self._workspace}

    def _base_observation(
        self,
        *,
        reward: float,
        workspace_files: dict[str, str],
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        feedback: str = "",
        failing_tests: list[str] | None = None,
        failure_details: list[str] | None = None,
    ) -> ReviewObservation:
        if self._task is None:
            raise RuntimeError("No active task.")

        return ReviewObservation(
            done=self._done,
            solved=self._solved,
            reward=reward,
            task_brief=self._task["task_brief"],
            workspace_files=workspace_files,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            feedback=feedback,
            failing_tests=failing_tests or [],
            failure_details=failure_details or [],
            task_id=self._task["id"],
            difficulty=self._task["difficulty"],
            tests_passed=self._last_public_passed,
            tests_total=len(self._task["public_tests"]),
            test_runs_used=self._state.test_runs_used,
            max_test_runs=self._task["max_test_runs"],
        )

    def _sync_state(self) -> None:
        self._state.workspace_manifest = build_workspace_summary(self._workspace)

    def _maybe_finish_for_step_budget(self, feedback: str) -> str:
        if self._task is None:
            return feedback
        if not self._done and self._state.step_count >= self._task["max_steps"]:
            self._done = True
            suffix = "Step budget exhausted."
            return f"{feedback} {suffix}".strip()
        return feedback

    def _handle_read_files(self, action: ReviewAction) -> ReviewObservation:
        assert self._task is not None
        requested_paths = action.paths or list(self._workspace)
        missing = [path for path in requested_paths if path not in self._workspace]
        workspace_files = self._workspace_view(requested_paths)
        if missing:
            feedback = self._maybe_finish_for_step_budget(
                f"Some files were not found: {', '.join(missing)}."
            )
            return self._base_observation(
                reward=0.0,
                workspace_files=workspace_files,
                stderr=f"Missing files: {', '.join(missing)}",
                exit_code=1,
                feedback=feedback,
            )

        feedback = self._maybe_finish_for_step_budget(
            f"Loaded {len(workspace_files)} workspace file(s)."
        )
        return self._base_observation(
            reward=0.0,
            workspace_files=workspace_files,
            stdout="\n".join(requested_paths),
            exit_code=0,
            feedback=feedback,
        )

    def _handle_update_files(self, action: ReviewAction) -> ReviewObservation:
        assert self._task is not None
        editable = set(self._task["editable_files"])
        proposed_files = action.files or {}
        if not proposed_files:
            feedback = self._maybe_finish_for_step_budget("No file updates were provided.")
            return self._base_observation(
                reward=0.0,
                workspace_files=self._workspace_view(),
                stderr="No files provided.",
                exit_code=1,
                feedback=feedback,
            )

        invalid_paths = [path for path in proposed_files if path not in editable]
        if invalid_paths:
            feedback = self._maybe_finish_for_step_budget(
                f"Update rejected. Only editable files may be changed: {', '.join(self._task['editable_files'])}."
            )
            return self._base_observation(
                reward=0.0,
                workspace_files=self._workspace_view(),
                stderr=f"Non-editable files requested: {', '.join(invalid_paths)}",
                exit_code=1,
                feedback=feedback,
            )

        self._workspace.update(proposed_files)
        self._sync_state()

        validation_task = {"editable_files": list(proposed_files)}
        validation = quality_report(validation_task, self._workspace)
        notes = validation["messages"][:3]
        note_text = f" Validation notes: {' | '.join(notes)}." if notes else ""
        feedback = self._maybe_finish_for_step_budget(
            f"Updated {len(proposed_files)} file(s).{note_text}"
        )
        return self._base_observation(
            reward=0.0,
            workspace_files=self._workspace_view(),
            stdout=f"Updated files: {', '.join(proposed_files)}",
            exit_code=0,
            feedback=feedback,
            failure_details=notes,
        )

    def _handle_run_tests(self) -> ReviewObservation:
        assert self._task is not None
        next_test_run = self._state.test_runs_used + 1
        should_check_hidden = next_test_run >= self._task["max_test_runs"]

        result = evaluate_workspace(
            self._task,
            self._workspace,
            run_hidden=False,
        )
        if result["public_ratio"] == 1.0 or should_check_hidden:
            result = evaluate_workspace(
                self._task,
                self._workspace,
                run_hidden=True,
            )

        self._state.test_runs_used = next_test_run
        self._last_public_passed = int(result["public_passed"])
        self._last_failing_tests = list(result["failing_tests"])
        self._last_failure_details = list(result["failure_details"])

        remaining_step_ratio = max(
            0.0,
            (self._task["max_steps"] - self._state.step_count) / self._task["max_steps"],
        )
        remaining_test_ratio = max(
            0.0,
            (self._task["max_test_runs"] - next_test_run) / self._task["max_test_runs"],
        )
        efficiency_score = (remaining_step_ratio + remaining_test_ratio) / 2
        final_score = min(1.0, float(result["score"]) + (0.10 * efficiency_score))

        self._solved = bool(result["success"])
        self._state.best_score = max(self._state.best_score, final_score)
        self._state.solved = self._solved
        self._state.tests_passed = max(self._state.tests_passed, int(result["public_passed"]))
        self._state.tests_total = int(result["public_total"])

        exhausted_tests = self._state.test_runs_used >= self._task["max_test_runs"]
        self._done = self._solved or exhausted_tests

        if result["hidden_checked"]:
            hidden_text = f" Hidden tests {result['hidden_passed']}/{result['hidden_total']}."
        else:
            hidden_text = " Hidden tests not checked yet."

        detail_text = ""
        if result["failure_details"]:
            detail_text = f" Details: {' | '.join(result['failure_details'][:2])}."

        if result["success"]:
            prefix = "Solved."
            status = "Public and hidden tests passed."
        elif exhausted_tests:
            prefix = "Test budget exhausted."
            status = "No more test runs remain."
        else:
            prefix = "Continue editing."
            status = "Make another workspace change before the next test run."

        feedback = self._maybe_finish_for_step_budget(
            f"{prefix} Test run {self._state.test_runs_used}/{self._task['max_test_runs']}. "
            f"Public tests {result['public_passed']}/{result['public_total']}.{hidden_text} "
            f"{status} Reward components include hidden-test progress and efficiency.{detail_text}"
        )

        return self._base_observation(
            reward=final_score,
            workspace_files=self._workspace_view(),
            stdout=result["stdout"],
            stderr=result["stderr"],
            exit_code=int(result["exit_code"]),
            feedback=feedback,
            failing_tests=result["failing_tests"],
            failure_details=result["failure_details"],
        )

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        difficulty: str = "easy",
        task_id: str | None = None,
        **_: object,
    ) -> ReviewObservation:
        self._task = self._select_task(difficulty=difficulty, seed=seed, task_id=task_id)
        self._workspace = _copy_workspace(self._task["workspace_files"])
        self._done = False
        self._solved = False
        self._last_public_passed = 0
        self._last_failing_tests = []
        self._last_failure_details = []
        self._state = ReviewState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            difficulty=self._task["difficulty"],
            best_score=0.0,
            solved=False,
            tests_passed=0,
            tests_total=len(self._task["public_tests"]),
            test_runs_used=0,
            max_test_runs=self._task["max_test_runs"],
            task_id=self._task["id"],
            workspace_manifest=build_workspace_summary(self._workspace),
        )

        return self._base_observation(
            reward=0.0,
            workspace_files=self._workspace_view(),
            feedback=(
                f"Workspace loaded. You have {self._task['max_steps']} total actions and "
                f"{self._task['max_test_runs']} test runs. Read files, update editable files, then run tests."
            ),
        )

    def step(
        self,
        action: ReviewAction,
        timeout_s: float | None = None,
        **_: object,
    ) -> ReviewObservation:
        del timeout_s
        if self._task is None:
            raise RuntimeError("Call reset() before step().")
        if self._done:
            raise RuntimeError("Episode already complete. Call reset().")

        self._state.step_count += 1
        action_type = (action.action_type or "read_files").lower()

        if action_type == "read_files":
            observation = self._handle_read_files(action)
        elif action_type == "update_files":
            observation = self._handle_update_files(action)
        elif action_type == "run_tests":
            observation = self._handle_run_tests()
        else:
            feedback = self._maybe_finish_for_step_budget(
                f"Unknown action_type `{action.action_type}`. Use read_files, update_files, or run_tests."
            )
            observation = self._base_observation(
                reward=0.0,
                workspace_files=self._workspace_view(),
                stderr=f"Unsupported action_type: {action.action_type}",
                exit_code=1,
                feedback=feedback,
            )

        self._sync_state()
        return observation

    @property
    def state(self) -> ReviewState:
        return self._state
