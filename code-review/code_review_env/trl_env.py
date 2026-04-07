from __future__ import annotations

import os
from typing import Any

try:
    from .client import CodeReviewEnvClient
    from .models import ReviewAction
except ImportError:
    from client import CodeReviewEnvClient
    from models import ReviewAction


ENV_URL = os.environ.get("ENV_URL", "http://localhost:7860")
SUPPORTS_CONCURRENT_SESSIONS = True


class CodeReviewToolEnv:
    def __init__(self) -> None:
        self._client = CodeReviewEnvClient(base_url=ENV_URL).sync()
        self._client.connect()
        self.reward = 0.0
        self.done = False
        self._summary = ""

    def reset(self, **kwargs: Any) -> str:
        difficulty = kwargs.get("difficulty", "easy")
        result = self._client.reset(difficulty=difficulty)
        self.reward = 0.0
        self.done = False
        self._summary = ""
        return result.observation.prompt

    def describe_fix(self, summary: str) -> str:
        """
        Record an optional short strategy note for the next code submission.

        Args:
            summary: A concise explanation of what you plan to change in the code
                or why the current implementation is failing.
        """
        if self.done:
            raise ValueError("Episode complete.")

        self._summary = summary
        return "Strategy recorded. Call submit_fix with revised code."

    def submit_fix(self, fixed_code: str | dict[str, str]) -> str:
        """
        Submit revised code for the active debugging task and receive test feedback.

        Args:
            fixed_code: The updated implementation. Use a single Python string for
                easy and medium tasks, or a filename-to-code dictionary for hard
                multi-file tasks.
        """
        if self.done:
            raise ValueError("Episode complete.")

        result = self._client.step(
            ReviewAction(
                fixed_code=fixed_code,
                summary=self._summary,
            )
        )
        self.reward = float(result.reward or 0.0)
        self.done = result.done
        return result.observation.feedback

    def __del__(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
