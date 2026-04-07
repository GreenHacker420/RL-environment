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
        self._bug_line: int | list[dict[str, Any]] = -1
        self._bug_type: str | list[str] = ""
        self._description = ""

    def reset(self, **kwargs: Any) -> str:
        difficulty = kwargs.get("difficulty", "easy")
        result = self._client.reset(difficulty=difficulty)
        self.reward = 0.0
        self.done = False
        self._bug_line = -1
        self._bug_type = ""
        self._description = ""
        return result.observation.prompt

    def identify_bug(
        self,
        bug_line: int | list[dict[str, Any]],
        bug_type: str | list[str],
        description: str,
    ) -> str:
        """
        Record the bug report that will be submitted with the final fix.

        Args:
            bug_line: A single line number for easy tasks or a list of bug report
                dictionaries for medium and hard tasks. Each dictionary can include
                line, file, bug_type, and description.
            bug_type: A single bug type string for easy tasks or a list of bug type
                strings for medium and hard tasks.
            description: A short summary of the bug report. For medium and hard tasks,
                include the key findings across all reported bugs.
        """
        if self.done:
            raise ValueError("Episode complete.")

        self._bug_line = bug_line
        self._bug_type = bug_type
        self._description = description
        return "Bug report recorded. Call submit_fix to finish the episode."

    def submit_fix(self, fixed_code: str | dict[str, str]) -> str:
        """
        Submit the final corrected code and complete the episode.

        Args:
            fixed_code: The corrected code as a single Python string for easy and
                medium tasks, or a filename-to-code dictionary for hard tasks.
        """
        if self.done:
            raise ValueError("Episode complete.")

        action = ReviewAction(
            bug_line=self._bug_line,
            bug_type=self._bug_type,
            description=self._description,
            fixed_code=fixed_code,
        )
        result = self._client.step(action)
        self.reward = float(result.reward or 0.0)
        self.done = result.done
        return result.observation.feedback

    def __del__(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
