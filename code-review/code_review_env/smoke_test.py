from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from .client import CodeReviewEnvClient
    from .models import ReviewAction
except ImportError:
    ROOT = Path(__file__).resolve().parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from client import CodeReviewEnvClient
    from models import ReviewAction


def main() -> None:
    client = CodeReviewEnvClient(base_url="http://localhost:7860").sync()
    with client:
        reset_result = client.reset(difficulty="easy", task_id="easy_missing_return")
        print("RESET")
        print(json.dumps(reset_result.observation.model_dump(), indent=2))

        action = ReviewAction(
            bug_line=2,
            bug_type="missing return",
            description="missing return result output",
            fixed_code="def square(n):\n    result = n * n\n    return result",
        )
        step_result = client.step(action)
        print("STEP")
        print(json.dumps(step_result.observation.model_dump(), indent=2))
        print("REWARD", step_result.reward)

        state = client.state()
        print("STATE")
        print(json.dumps(state.model_dump(), indent=2))


if __name__ == "__main__":
    main()
