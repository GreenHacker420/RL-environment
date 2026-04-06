import random
from uuid import uuid4
from typing import Optional, Dict, Any

from openenv.core.env_server.interfaces import Environment
from .models import CodeReviewAction, CodeReviewObservation, CodeReviewState
from .tasks import TASKS
from .graders import grade_easy, grade_medium, grade_hard

class CodeReviewEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = CodeReviewState(episode_id=str(uuid4()), step_count=0)
        self._current_task = None

    def reset(self, difficulty: str = "easy", **kwargs) -> CodeReviewObservation:
        self._state = CodeReviewState(
            episode_id=str(uuid4()),
            step_count=0,
            difficulty=difficulty,
            task_id=random.randint(0, len(TASKS.get(difficulty, TASKS["easy"])) - 1)
        )
        
        self._current_task = TASKS[self._state.difficulty][self._state.task_id]
        
        return CodeReviewObservation(
            content=self._current_task.content,
            feedback=f"Task: {self._current_task.name}. Please identify and fix the bugs.",
            metadata={"difficulty": self._state.difficulty}
        )

    def step(self, action: CodeReviewAction) -> CodeReviewObservation:
        self._state.step_count += 1
        
        # In a real environment, 'identify' might just store info, 
        # and 'submit' would trigger grading.
        # For simplicity, any action here triggers grading if it's a submission.
        
        if action.action_type == "submit":
            if self._state.difficulty == "easy":
                score, feedback = grade_easy(action, self._current_task.ground_truth, self._current_task)
            elif self._state.difficulty == "medium":
                score, feedback = grade_medium(action, self._current_task.ground_truth, self._current_task)
            else:
                score, feedback = grade_hard(action, self._current_task.ground_truth, self._current_task)
            
            return CodeReviewObservation(
                content=None,
                feedback=feedback,
                done=True,
                reward=score
            )
        
        # Record identification in history
        if action.action_type == "identify":
            self._state.history.append({
                "bug_line": action.bug_line,
                "bug_type": action.bug_type,
                "description": action.description
            })
            return CodeReviewObservation(
                content=None,
                feedback="Bug identified. Continue or submit fix.",
                done=False,
                reward=0.0
            )

        return CodeReviewObservation(
            content=None,
            feedback="Unknown action type.",
            done=False,
            reward=0.0
        )

    @property
    def state(self) -> CodeReviewState:
        return self._state
