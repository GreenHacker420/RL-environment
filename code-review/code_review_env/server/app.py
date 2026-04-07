from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn
from openenv.core.env_server import create_fastapi_app

try:
    from ..models import ReviewAction, ReviewObservation
    from .environment import CodeReviewEnv
except ImportError:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from models import ReviewAction, ReviewObservation
    from server.environment import CodeReviewEnv


app = create_fastapi_app(
    env=CodeReviewEnv,
    action_cls=ReviewAction,
    observation_cls=ReviewObservation,
    max_concurrent_envs=64,
)


def main(host: str = "0.0.0.0", port: int | None = None) -> None:
    resolved_port = port if port is not None else int(os.environ.get("PORT", "7860"))
    uvicorn.run(app, host=host, port=resolved_port)


if __name__ == "__main__":
    main()
