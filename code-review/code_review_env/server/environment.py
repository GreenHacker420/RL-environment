from __future__ import annotations

import random
import sys
from pathlib import Path
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment

try:
    from ..graders import evaluate_submission
    from ..models import ReviewAction, ReviewObservation, ReviewState
    from ..tasks import build_observation_prompt, get_task_by_id, get_tasks_by_difficulty
except ImportError:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from graders import evaluate_submission
    from models import ReviewAction, ReviewObservation, ReviewState
    from tasks import build_observation_prompt, get_task_by_id, get_tasks_by_difficulty


def _clone_code(prompt: str | dict[str, str]) -> str | dict[str, str]:
    if isinstance(prompt, dict):
        return dict(prompt)
    return str(prompt)


class CodeReviewEnv(Environment[ReviewAction, ReviewObservation, ReviewState]):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        super().__init__()
        self._task: dict | None = None
        self._current_code: str | dict[str, str] = ""
        self._done = False
        self._best_public_ratio = 0.0
        self._state = ReviewState(
            episode_id=str(uuid4()),
            step_count=0,
            difficulty="easy",
            current_score=0.0,
            best_score=0.0,
            task_id="",
            max_attempts=0,
            tests_passed=0,
            tests_total=0,
        )

    def _select_task(self, difficulty: str, seed: int | None, task_id: str | None) -> dict:
        if task_id is not None:
            return get_task_by_id(task_id)

        candidates = get_tasks_by_difficulty(difficulty)
        if not candidates:
            raise ValueError(f"Unknown difficulty: {difficulty}")

        chooser = random.Random(seed) if seed is not None else random
        return chooser.choice(candidates)

    def _apply_submission(self, action: ReviewAction) -> str | dict[str, str]:
        if self._task is None:
            raise RuntimeError("Call reset() before step().")

        if self._task["task_kind"] in {"function", "class"}:
            return str(action.fixed_code)

        updated = dict(self._current_code) if isinstance(self._current_code, dict) else dict(self._task["prompt"])
        if isinstance(action.fixed_code, dict):
            updated.update(action.fixed_code)
            return updated
        return {}

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        difficulty: str = "easy",
        task_id: str | None = None,
        **_: object,
    ) -> ReviewObservation:
        self._task = self._select_task(difficulty=difficulty, seed=seed, task_id=task_id)
        self._current_code = _clone_code(self._task["prompt"])
        self._done = False
        self._best_public_ratio = 0.0
        self._state = ReviewState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            difficulty=self._task["difficulty"],
            current_score=0.0,
            best_score=0.0,
            task_id=self._task["id"],
            max_attempts=self._task["max_attempts"],
            tests_passed=0,
            tests_total=len(self._task["public_tests"]),
        )

        return ReviewObservation(
            done=False,
            reward=0.0,
            prompt=build_observation_prompt(self._task, self._current_code),
            feedback=(
                f"New PR loaded. You have {self._task['max_attempts']} attempts. "
                f"Public tests start at 0/{len(self._task['public_tests'])}."
            ),
            task_id=self._task["id"],
            difficulty=self._task["difficulty"],
            attempt=0,
            max_attempts=self._task["max_attempts"],
            tests_passed=0,
            tests_total=len(self._task["public_tests"]),
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

        self._current_code = self._apply_submission(action)
        graded_action = ReviewAction(
            fixed_code=self._current_code,
            summary=action.summary,
            metadata=action.metadata,
        )
        result = evaluate_submission(
            self._task,
            graded_action,
            previous_best_public_ratio=self._best_public_ratio,
        )

        self._state.step_count += 1
        self._state.current_score = float(result["score"])
        self._state.best_score = max(self._state.best_score, float(result["score"]))
        self._state.tests_passed = max(self._state.tests_passed, int(result["public_passed"]))
        self._state.tests_total = int(result["public_total"])
        self._best_public_ratio = max(self._best_public_ratio, float(result["public_ratio"]))

        exhausted = self._state.step_count >= self._task["max_attempts"]
        self._done = bool(result["success"]) or exhausted
        status = "Solved." if result["success"] else ("Attempts exhausted." if exhausted else "Continue refining the code.")
        feedback = (
            f"Attempt {self._state.step_count}/{self._task['max_attempts']}. "
            f"{result['feedback']} "
            f"{status}"
        )

        return ReviewObservation(
            done=self._done,
            reward=float(result["score"]),
            prompt=build_observation_prompt(self._task, self._current_code),
            feedback=feedback,
            task_id=self._task["id"],
            difficulty=self._task["difficulty"],
            attempt=self._state.step_count,
            max_attempts=self._task["max_attempts"],
            tests_passed=int(result["public_passed"]),
            tests_total=int(result["public_total"]),
        )

    @property
    def state(self) -> ReviewState:
        return self._state
