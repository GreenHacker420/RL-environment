from __future__ import annotations

import hashlib
import os
import random
import uuid

from openenv.core.env_server import Environment

from graders import grade_response
from models import DrugAction, DrugObservation, DrugState
from tasks import TaskConfig, TaskLoader


def _seed_from_episode_id(episode_id: str) -> int:
    digest = hashlib.sha256(episode_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


class DrugInteractionEnv(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        self._task_loader = TaskLoader()
        initial_seed = int.from_bytes(os.urandom(8), byteorder="big", signed=False)
        self._rng = random.Random(initial_seed)
        self._episode_id: str | None = None
        self._step_count = 0
        self._task: TaskConfig | None = None
        self._current_score = 0.0
        self._safety_violations = 0

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        **_: object,
    ) -> DrugObservation:
        self._episode_id = episode_id or str(uuid.uuid4())
        if seed is not None:
            self._rng.seed(seed)
        else:
            self._rng.seed(_seed_from_episode_id(self._episode_id))
        self._task = self._task_loader.sample(self._rng)
        self._step_count = 0
        self._current_score = 0.0
        return DrugObservation(
            done=False,
            reward=0.0,
            prompt=self._task.prompt,
            task_id=self._task.id,
            task_type=self._task.task_type,
            feedback="",
            partial_score=0.0,
            metadata={
                "episode_id": self._episode_id,
                "difficulty_score": self._task.difficulty_score,
                "input_data": self._task.input_data,
            },
        )

    def step(
        self,
        action: DrugAction,
        timeout_s: float | None = None,
        **_: object,
    ) -> DrugObservation:
        if self._task is None or self._episode_id is None:
            raise RuntimeError("Environment must be reset before step().")
        _ = timeout_s

        score, feedback = grade_response(self._task, action)
        self._step_count += 1
        self._current_score = score

        if "SAFETY VIOLATION" in feedback:
            self._safety_violations += 1
        elif (
            self._task.task_type == "hard"
            and self._task.ground_truth.get("triage") == "emergency"
            and action.triage.lower() == "normal"
        ):
            self._safety_violations += 1

        return DrugObservation(
            done=True,
            reward=score,
            prompt=self._task.prompt,
            task_id=self._task.id,
            task_type=self._task.task_type,
            feedback=feedback,
            partial_score=score,
            metadata={
                "episode_id": self._episode_id,
                "difficulty_score": self._task.difficulty_score,
                "input_data": self._task.input_data,
                "ground_truth": self._task.ground_truth,
                "action": action.model_dump(),
            },
        )

    @property
    def state(self) -> DrugState:
        return DrugState(
            episode_id=self._episode_id,
            step_count=self._step_count,
            task_type=self._task.task_type if self._task is not None else "",
            current_score=self._current_score,
            safety_violations=self._safety_violations,
        )
