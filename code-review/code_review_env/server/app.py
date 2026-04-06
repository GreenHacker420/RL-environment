# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""FastAPI application for the Code Review Environment."""

try:
    from openenv.core.env_server.http_server import create_app
except ImportError as e:
    raise ImportError(
        "openenv is required. Install with 'pip install openenv'"
    ) from e

try:
    from ..models import CodeReviewAction, CodeReviewObservation
    from .environment import CodeReviewEnvironment
except ImportError:
    from models import CodeReviewAction, CodeReviewObservation
    from server.environment import CodeReviewEnvironment

# Create the app
app = create_app(
    CodeReviewEnvironment,
    CodeReviewAction,
    CodeReviewObservation,
    env_name="code_review_env",
    max_concurrent_envs=64,
)

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
