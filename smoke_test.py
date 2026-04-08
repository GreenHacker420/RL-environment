from __future__ import annotations

import json
import os
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
    client = CodeReviewEnvClient(base_url=os.getenv("ENV_URL", "http://localhost:7860")).sync()
    with client:
        reset_result = client.reset(difficulty="easy", task_id="easy_implementation_discount", seed=42)
        print("RESET")
        print(json.dumps(reset_result.observation.model_dump(), indent=2))
        task_brief = reset_result.observation.task_brief
        workspace_path = reset_result.observation.workspace_manifest[0].split(" (", 1)[0]
        function_name = task_brief.split("`")[1].split("(")[0]

        read_result = client.step(ReviewAction(action_type="read_files", paths=[workspace_path]))
        print("READ")
        print(json.dumps(read_result.observation.model_dump(), indent=2))

        partial_update = client.step(
            ReviewAction(
                action_type="update_files",
                files={
                    workspace_path: (
                        f"def {function_name}(subtotal, has_coupon):\n"
                        "    return round(subtotal, 2)\n"
                    )
                },
                summary="Intentionally incomplete implementation to verify partial progress.",
            )
        )
        print("UPDATE 1")
        print(json.dumps(partial_update.observation.model_dump(), indent=2))

        lint_result = client.step(ReviewAction(action_type="run_lint"))
        print("LINT 1")
        print(json.dumps(lint_result.observation.model_dump(), indent=2))

        first_test = client.step(ReviewAction(action_type="run_tests"))
        print("TEST 1")
        print(json.dumps(first_test.observation.model_dump(), indent=2))
        print("REWARD", first_test.reward)

        discount_percent = int(task_brief.split("apply a ")[1].split("%")[0])
        rate = discount_percent / 100
        corrected_code = (
            f"def {function_name}(subtotal, has_coupon):\n"
            f"    if has_coupon:\n"
            f"        subtotal = subtotal * (1 - {rate})\n"
            f"    return round(subtotal, 2)\n"
        )
        final_update = client.step(
            ReviewAction(
                action_type="update_files",
                files={workspace_path: corrected_code},
                summary="Apply the coupon only when requested and round to 2 decimals.",
            )
        )
        print("UPDATE 2")
        print(json.dumps(final_update.observation.model_dump(), indent=2))

        second_lint = client.step(ReviewAction(action_type="run_lint"))
        print("LINT 2")
        print(json.dumps(second_lint.observation.model_dump(), indent=2))

        second_test = client.step(ReviewAction(action_type="run_tests"))
        print("TEST 2")
        print(json.dumps(second_test.observation.model_dump(), indent=2))
        print("REWARD", second_test.reward)

        state = client.state()
        print("STATE")
        print(json.dumps(state.model_dump(), indent=2))


if __name__ == "__main__":
    main()
