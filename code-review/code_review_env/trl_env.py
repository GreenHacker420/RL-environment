from __future__ import annotations

import os
from typing import Any

try:
    from .client import CodeReviewEnvClient
    from .models import ReviewAction
    from .tasks import render_workspace
except ImportError:
    from client import CodeReviewEnvClient
    from models import ReviewAction
    from tasks import render_workspace


ENV_URL = os.environ.get("ENV_URL", "http://localhost:7860")
SUPPORTS_CONCURRENT_SESSIONS = True


def _render_workspace_block(files: dict[str, str]) -> str:
    if not files:
        return "No workspace files returned."
    return render_workspace(files)


class CodeReviewToolEnv:
    def __init__(self) -> None:
        self._client = CodeReviewEnvClient(base_url=ENV_URL).sync()
        self._client.connect()
        self._workspace_cache: dict[str, str] = {}
        self.reward = 0.0
        self.done = False

    def reset(self, **kwargs: Any) -> str:
        difficulty = kwargs.get("difficulty", "easy")
        task_id = kwargs.get("task_id")
        result = self._client.reset(difficulty=difficulty, task_id=task_id)
        observation = result.observation
        self._workspace_cache = {}
        manifest_paths = [entry.split(" (", 1)[0] for entry in observation.workspace_manifest]
        if manifest_paths:
            read_result = self._client.step(ReviewAction(action_type="read_files", paths=manifest_paths))
            observation = read_result.observation
            self._workspace_cache.update(observation.workspace_files)
        self.reward = 0.0
        self.done = False
        return (
            f"{observation.task_brief}\n\n"
            f"Workspace:\n{_render_workspace_block(self._workspace_cache)}\n\n"
            f"Test runs available: {observation.test_runs_used}/{observation.max_test_runs}\n"
            f"Feedback: {observation.feedback}"
        )

    def update_files(self, files: dict[str, str], summary: str = "") -> str:
        """
        Update one or more editable workspace files before running tests.

        Args:
            files: Mapping from workspace file path to the full replacement file
                contents for that path. Only editable files from the task may be
                updated.
            summary: Optional short note describing the intended change.
        """
        if self.done:
            raise ValueError("Episode complete.")

        result = self._client.step(
            ReviewAction(
                action_type="update_files",
                files=files,
                summary=summary,
            )
        )
        self.reward = float(result.reward or 0.0)
        self.done = result.done
        observation = result.observation
        self._workspace_cache.update(observation.workspace_files)
        return (
            f"{observation.feedback}\n\n"
            f"Workspace:\n{_render_workspace_block(self._workspace_cache)}"
        )

    def run_lint(self) -> str:
        """
        Execute deterministic lint checks against the editable workspace files.

        Args:
            None.
        """
        if self.done:
            raise ValueError("Episode complete.")

        result = self._client.step(ReviewAction(action_type="run_lint"))
        self.reward = float(result.reward or 0.0)
        self.done = result.done
        observation = result.observation
        issues = "None"
        if observation.lint_issues:
            issues = "\n- " + "\n- ".join(observation.lint_issues)
        return (
            f"{observation.feedback}\n"
            f"Lint issues:{issues}\n"
            f"Exit code: {observation.exit_code}"
        )

    def run_tests(self) -> str:
        """
        Execute the task's deterministic test suite against the current workspace.

        Args:
            None.
        """
        if self.done:
            raise ValueError("Episode complete.")

        result = self._client.step(ReviewAction(action_type="run_tests"))
        self.reward = float(result.reward or 0.0)
        self.done = result.done
        observation = result.observation
        failure_block = ""
        if observation.failure_details:
            failure_block = "\nFailure details:\n- " + "\n- ".join(observation.failure_details)
        return (
            f"{observation.feedback}\n"
            f"Reward: {self.reward:.2f}\n"
            f"Public tests: {observation.tests_passed}/{observation.tests_total}\n"
            f"Test runs used: {observation.test_runs_used}/{observation.max_test_runs}"
            f"{failure_block}"
        )

    def __del__(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
