import os
import json
from typing import Optional, Dict, Any
from .client import CodeReviewEnv
from .models import CodeReviewAction

ENV_URL = os.environ.get("ENV_URL", "http://localhost:7860")
SUPPORTS_CONCURRENT_SESSIONS: bool = True

class CodeReviewGRPOEnv:
    def __init__(self):
        self.client = CodeReviewEnv(base_url=ENV_URL)
        self.reward = 0.0
        self.done = False
        self._last_obs = None

    def reset(self, **kwargs) -> Optional[str]:
        """
        Reset the environment for a new episode.
        Args:
            difficulty: The difficulty level (easy, medium, hard).
        """
        difficulty = kwargs.get("difficulty", "easy")
        result = self.client.reset(difficulty=difficulty)
        self.reward = 0.0
        self.done = False
        self._last_obs = result.observation
        
        content = self._last_obs.content
        if isinstance(content, dict):
            content_str = json.dumps(content, indent=2)
        else:
            content_str = str(content)
            
        return f"{self._last_obs.feedback}\n\nCode to review:\n{content_str}"

    def identify_bug(self, bug_line: int, bug_type: str, description: str, file_path: Optional[str] = None) -> str:
        """Identify a bug in the code snippet.
        Args:
            bug_line: The line number where the bug occurs
            bug_type: Type of bug: syntax, logic, runtime, or style
            description: Brief description of the bug
            file_path: (Optional) The filename for multi-file tasks
        Returns:
            Feedback on whether the identification is correct.
        """
        if self.done:
            raise ValueError("Episode complete.")

        action = CodeReviewAction(
            action_type="identify",
            bug_line=bug_line,
            bug_type=bug_type,
            description=description,
            file_path=file_path
        )
        result = self.client.step(action)
        self.reward = result.reward
        self.done = result.done
        return result.observation.feedback

    def submit_fix(self, fixed_code: str) -> str:
        """Submit the corrected version of the code.
        Args:
            fixed_code: The complete corrected code as a string
        Returns:
            Test results showing pass/fail for each test case.
        """
        if self.done:
            raise ValueError("Episode complete.")

        action = CodeReviewAction(
            action_type="submit",
            fixed_code=fixed_code
        )
        result = self.client.step(action)
        self.reward = result.reward
        self.done = result.done
        return result.observation.feedback
