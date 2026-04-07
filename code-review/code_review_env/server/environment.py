from __future__ import annotations

import random
import sys
from uuid import uuid4
from pathlib import Path

from openenv.core.env_server.interfaces import Environment

try:
    from ..graders import grade_easy, grade_hard, grade_medium
    from ..models import ReviewAction, ReviewObservation, ReviewState
    from ..tasks import get_tasks_by_difficulty, render_prompt
except ImportError:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from graders import grade_easy, grade_hard, grade_medium
    from models import ReviewAction, ReviewObservation, ReviewState
    from tasks import get_tasks_by_difficulty, render_prompt


class CodeReviewEnv(Environment[ReviewAction, ReviewObservation, ReviewState]):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        super().__init__()
        self._task: dict | None = None
        self._done = False
        self._state = ReviewState(
            episode_id=str(uuid4()),
            step_count=0,
            difficulty="easy",
            current_score=0.0,
        )

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        difficulty: str = "easy",
        **_: object,
    ) -> ReviewObservation:
        candidates = get_tasks_by_difficulty(difficulty)
        if not candidates:
            raise ValueError(f"Unknown difficulty: {difficulty}")

        chooser = random.Random(seed) if seed is not None else random
        self._task = chooser.choice(candidates)
        self._done = False
        self._state = ReviewState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            difficulty=difficulty,
            current_score=0.0,
        )

        return ReviewObservation(
            done=False,
            reward=0.0,
            prompt=render_prompt(self._task["prompt"]),
            feedback="Identify the bug location, classify the bug type, and submit corrected code.",
            task_id=self._task["id"],
            difficulty=difficulty,
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

        graders = {
            "easy": grade_easy,
            "medium": grade_medium,
            "hard": grade_hard,
        }
        grade = graders[self._task["difficulty"]]
        score, feedback = grade(self._task, action)

        self._done = True
        self._state.step_count = 1
        self._state.current_score = score

        return ReviewObservation(
            done=True,
            reward=score,
            prompt="",
            feedback=feedback,
            task_id=self._task["id"],
            difficulty=self._task["difficulty"],
        )

    @property
    def state(self) -> ReviewState:
        return self._state
