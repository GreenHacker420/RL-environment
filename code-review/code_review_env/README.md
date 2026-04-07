---
title: CodeReviewEnv
emoji: "🧪"
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 7860
base_path: /web
tags:
  - openenv
---

# CodeReviewEnv

CodeReviewEnv is an OpenEnv benchmark for iterative code review and debugging.
An agent receives a buggy pull request, submits revised code, gets test feedback,
and refines the solution over multiple attempts.

This is not a one-shot answer matcher. The environment scores code primarily by
running deterministic tests against the submitted implementation.

## Why this environment

Real software engineering is iterative:

- inspect buggy code
- make a change
- run tests
- inspect failures
- refine the fix

CodeReviewEnv models that loop directly. It is closer to real debugging than a
single-step classification task and provides shaped reward over a trajectory.

## Task design

The benchmark contains 12 hardcoded seed tasks across 3 difficulty tiers:

- Easy: 5 single-function tasks with one bug each
- Medium: 4 class-based tasks with multiple interacting bugs
- Hard: 3 multi-file tasks with cross-module integration failures

Each task includes:

- PR-style title and description
- buggy code
- public tests used for intermediate feedback
- hidden tests used for final validation
- deterministic attempt limits

Attempt limits:

- easy: 3
- medium: 4
- hard: 4

## Interaction loop

Each episode works like this:

1. `reset()` returns a buggy pull request with code and public test descriptions.
2. The agent submits revised code with `step(action)`.
3. The environment parses the submission and runs tests in a subprocess.
4. The environment returns reward and feedback.
5. The episode ends when all tests pass or attempts are exhausted.

## Reward design

Reward is in `[0.0, 1.0]` and is shaped at every step.

The score is composed from:

- public test progress
- syntax and import validity
- improvement over the best previous public-test score

When all public tests pass, hidden tests are also checked and affect the final
success condition.

This means the agent gets useful partial credit before solving the whole task.

## Action space

`ReviewAction` has two fields:

- `fixed_code`
  full revised code submission
  use a string for easy and medium tasks
  use a filename-to-code dictionary for hard multi-file tasks
- `summary`
  optional short explanation of what changed

## Observation space

`ReviewObservation` includes:

- `prompt`
  PR context, current code, and public test descriptions
- `feedback`
  test feedback from the last submission
- `reward`
- `done`
- `task_id`
- `difficulty`
- `attempt`
- `max_attempts`
- `tests_passed`
- `tests_total`

## State space

`ReviewState` includes:

- `episode_id`
- `step_count`
- `difficulty`
- `current_score`
- `best_score`
- `task_id`
- `max_attempts`
- `tests_passed`
- `tests_total`

## Built-in UI and routes

The server exposes the default OpenEnv web UI:

- `/web/` for the interactive Gradio UI
- `/docs` for Swagger UI
- `/redoc` for ReDoc
- `/health` for health checks
- `/reset` to start a new episode
- `/step` to submit a revision
- `/state` to inspect the current environment state
- `/ws` for the WebSocket client interface

`/` redirects to `/web/` when the web interface is enabled.

## Run locally

From the project root:

```bash
openenv validate
python server/app.py
```

Then open:

- `http://localhost:7860/web/`
- `http://localhost:7860/docs`

## Docker

Build:

```bash
docker build -t code-review-env .
```

Run:

```bash
docker run --rm -p 7860:7860 code-review-env
```

## Quick smoke test

With the server running locally:

```bash
python smoke_test.py
```

The smoke test:

- resets to a known easy task
- submits one incorrect revision and gets partial reward
- submits a correct revision and finishes the episode
- prints the final state

## Python client

Example:

```python
from code_review_env import CodeReviewEnv, ReviewAction

client = CodeReviewEnv(base_url="http://localhost:7860").sync()

with client:
    reset_result = client.reset(difficulty="easy")
    prompt = reset_result.observation.prompt

    result = client.step(
        ReviewAction(
            fixed_code="def square(n):\n    return n * n",
            summary="Return the computed value.",
        )
    )
    print(result.reward, result.done, result.observation.feedback)
```

## Baseline inference

`inference.py` runs a reproducible baseline with the OpenAI client and the
required structured stdout format.

Required environment variables:

- `HF_TOKEN` or `OPENAI_API_KEY`
- `API_BASE_URL`
- `MODEL_NAME`

Example:

```bash
export HF_TOKEN=your_token
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
python inference.py --url http://localhost:7860 --episodes 12 --seed 42
```

The script writes `results.json` with:

- `mean_score`
- `std_score`
- per-difficulty breakdown
- episode-level details

## Validation checklist

Before submission:

```bash
openenv validate
docker build .
curl http://localhost:7860/health
python smoke_test.py
```

For the deployed Space:

```bash
curl https://greenhacker-code-review-env.hf.space/health
curl -X POST https://greenhacker-code-review-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Baseline scores

Run `inference.py` and paste the resulting aggregate numbers here before final
submission.
