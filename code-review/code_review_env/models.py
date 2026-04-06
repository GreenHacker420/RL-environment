from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from openenv.core.env_server.types import State as BaseState

@dataclass
class CodeReviewAction:
    action_type: str  # "identify" or "submit"
    bug_line: Optional[int] = None
    bug_type: Optional[str] = None
    description: Optional[str] = None
    fixed_code: Optional[str] = None
    file_path: Optional[str] = None

@dataclass
class CodeReviewObservation:
    content: Any  # Can be a string (code) or a dict (multi-file)
    feedback: str = ""
    done: bool = False
    reward: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CodeReviewState(BaseState):
    difficulty: str = "easy"
    task_id: int = 0
    history: List[Dict[str, Any]] = field(default_factory=list)
