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

CodeReviewEnv is an OpenEnv environment for iterative code review and debugging.
An agent receives a buggy pull request, submits revised code, gets automated test
feedback, and improves the solution over multiple attempts.

The environment is designed to model a real software engineering workflow rather
than a one-shot code quiz. The main signal comes from execution-based grading:
submitted code is parsed and tested in a subprocess, and reward reflects real
progress on the task.

## Why this benchmark

Most code benchmarks are single-turn. Real debugging is not.

In practice, engineers:

1. inspect buggy code
2. make a change
3. run tests
4. inspect failures
5. refine the fix

CodeReviewEnv turns that loop into an RL environment with shaped rewards and
clean episode boundaries.

## Environment summary

- Domain: code review / debugging
- API: OpenEnv `reset()` / `step()` / `state()`
- Interaction style: iterative, multi-step
- Evaluation: deterministic execution-based grading
- Deployment target: Hugging Face Space with Docker
- Client mode: WebSocket

## Task set

The benchmark contains 12 seed tasks across 3 difficulty tiers.

| Difficulty | Count | Shape | Examples |
| --- | ---: | --- | --- |
| Easy | 5 | single Python function, one bug | off-by-one, missing return, wrong operator |
| Medium | 4 | one Python class, multiple interacting bugs | `Stack`, `BankAccount`, `LinkedList`, `FileProcessor` |
| Hard | 3 | two short Python modules with integration failures | `calculator + validator`, `parser + formatter`, `auth + session` |

Each task includes:

- PR-style title and description
- developer note or reviewer context
- buggy code
- public tests for intermediate feedback
- hidden tests for final validation
- deterministic attempt limit

Attempt limits:

- easy: 3
- medium: 4
- hard: 4

## Core interaction loop

Each episode works like this:

1. `reset()` returns PR context, buggy code, and public test descriptions.
2. The agent submits revised code with `step(action)`.
3. The environment parses the submission and executes public tests.
4. The agent receives:
   - reward
   - tests passed / total
   - failure summary
   - updated prompt containing the current code
5. The episode ends when:
   - all public and hidden tests pass, or
   - the attempt limit is reached

This gives useful trajectory-level learning signal instead of a single binary score.

## Reward design

Reward is always in `[0.0, 1.0]`.

Current scoring is based on:

- `0.75 * test_signal`
- `0.15 * syntax_and_import_validity`
- `0.10 * improvement_over_previous_best_public_score`

Notes:

- Public tests drive the intermediate reward.
- Hidden tests are used once public tests pass to decide final success.
- Invalid Python receives `0.0`.
- Partial progress receives partial reward.

This makes the reward function dense enough for RL while still being grounded in
actual code behavior.

## Action space

The action model is intentionally simple.

`ReviewAction`:

- `fixed_code`
  full revised code submission
  use a string for easy and medium tasks
  use a filename-to-code map for hard tasks
- `summary`
  optional short explanation of the attempted fix

Example:

```python
ReviewAction(
    fixed_code="def square(n):\n    return n * n",
    summary="Return the computed value.",
)
```

## Observation space

`ReviewObservation` contains:

- `prompt`
  PR context, current code, and public test descriptions
- `feedback`
  latest execution feedback
- `reward`
- `done`
- `task_id`
- `difficulty`
- `attempt`
- `max_attempts`
- `tests_passed`
- `tests_total`

## State space

`ReviewState` contains:

- `episode_id`
- `step_count`
- `difficulty`
- `current_score`
- `best_score`
- `task_id`
- `max_attempts`
- `tests_passed`
- `tests_total`

## Repository layout

- [tasks.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/tasks.py)
  task bank, PR metadata, public tests, hidden tests
- [graders.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/graders.py)
  execution-based evaluation logic
- [models.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/models.py)
  typed action, observation, and state models
- [server/environment.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/server/environment.py)
  main OpenEnv environment loop
- [client.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/client.py)
  WebSocket client
- [trl_env.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/trl_env.py)
  TRL tool environment wrapper
- [inference.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/inference.py)
  reproducible baseline runner
- [smoke_test.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/smoke_test.py)
  local sanity test

## Built-in UI and routes

The server exposes the default OpenEnv web UI:

- `/web/` interactive Gradio UI
- `/docs` Swagger UI
- `/redoc` ReDoc
- `/health` health check
- `/reset` start an episode
- `/step` submit a revision
- `/state` inspect current state
- `/ws` WebSocket client endpoint

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

## Run with Docker

Build:

```bash
docker build -t code-review-env .
```

Run:

```bash
docker run --rm -p 7860:7860 code-review-env
```

## Quick smoke test

With the server running:

```bash
python smoke_test.py
```

The smoke test:

1. resets to a known easy task
2. submits one incorrect revision and gets partial reward
3. submits a correct revision and finishes the episode
4. prints final state

## Python client example

```python
from code_review_env import CodeReviewEnv, ReviewAction

client = CodeReviewEnv(base_url="http://localhost:7860").sync()

with client:
    reset_result = client.reset(difficulty="easy")
    print(reset_result.observation.prompt)

    result = client.step(
        ReviewAction(
            fixed_code="def square(n):\n    return n * n",
            summary="Return the computed value.",
        )
    )
    print(result.reward)
    print(result.done)
    print(result.observation.feedback)
```

## Manual API testing

Reset:

```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"difficulty":"easy"}'
```

Step:

```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "fixed_code": "def square(n):\n    result = n * n\n    return result",
      "summary": "Return the computed result.",
      "metadata": {}
    }
  }'
```

State:

```bash
curl http://localhost:7860/state
```

## TRL integration

[trl_env.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/trl_env.py) provides `CodeReviewToolEnv` for TRL `environment_factory`.

Exposed tool methods:

- `describe_fix`
- `submit_fix`

That wrapper keeps the interface narrow and tool-friendly for multi-turn training.

## Baseline inference

[inference.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/inference.py) runs a reproducible baseline using the OpenAI client and emits the required structured logs:

- `[START]`
- `[STEP]`
- `[END]`

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
python smoke_test.py
```

Recommended checks:

```bash
curl http://localhost:7860/health
curl -X POST http://localhost:7860/reset -H "Content-Type: application/json" -d '{}'
```

For the deployed Space:

```bash
curl https://greenhacker-code-review-env.hf.space/health
curl -X POST https://greenhacker-code-review-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Hugging Face Space

The project is configured as a Docker Space and exposes the OpenEnv UI at `/web/`.

Once deployed, verify:

- `/health` returns `200`
- `/reset` returns an observation
- `/web/` loads
- `/docs` loads

## Current limitations

- Tasks are still from a fixed curated bank, not generated variants.
- Hidden tests are deterministic but not yet templated per seed.
- The benchmark currently favors full-file submissions over patch application.

Those are acceptable for Round 1, but the next improvement would be templated task
variants with the same execution-based grading loop.

## Baseline scores

Run [inference.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/inference.py) and paste the resulting aggregate numbers here before final submission.

- Mean score: pending
- Std score: pending
- Easy: pending
- Medium: pending
- Hard: pending
