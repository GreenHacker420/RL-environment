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

CodeReviewEnv is a guided Python coding workspace built with OpenEnv. An agent receives a small local workspace, edits files, runs deterministic tests, and learns from structured execution feedback over multiple steps.

The environment is closer to a task-scaffolded coding workspace than to a
static code quiz. Code review remains one supported task family, but the core
benchmark is broader: implementation, repair, and integration work inside small
Python workspaces.

## Why This Environment Exists

Most code benchmarks are single-turn. Real coding work is not.

Engineers usually:

1. inspect files
2. make a change
3. run tests
4. inspect failures
5. refine the solution

CodeReviewEnv turns that loop into an RL environment with explicit workspace
tools, deterministic grading, and trajectory-level reward.

## Judging Criteria Mapping

### Real-world utility

- The task domain is real software work: implementing functions, repairing
  regressions, and fixing multi-file integrations.
- The agent operates on files and test feedback, not answer labels.
- Reward is grounded in code execution and deterministic checks.

### Task and grader quality

- The benchmark contains easy, medium, and hard task templates.
- Every task has public tests, hidden tests, and deterministic grading.
- Reward is always in `[0.0, 1.0]`.
- Tasks span implementation, repair, and integration instead of only one bug
  pattern.

### Environment design

- Episodes are multi-step.
- `read_files`, `update_files`, and `run_tests` are explicit actions.
- Reward is shaped mainly on `run_tests`, with intermediate progress signal.
- Episodes terminate on success, test-budget exhaustion, or step-budget exhaustion.

### Code quality and spec compliance

- Typed OpenEnv models are defined in [models.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/models.py).
- The environment implements `reset()`, `step()`, and `state()`.
- [openenv.yaml](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/openenv.yaml) is included.
- The repo ships with Docker, a baseline inference script, and a smoke test.

### Creativity and novelty

- This is not a freeform REPL and not a static answer-matching benchmark.
- It combines workspace inspection, controlled editing, and structured testing
  into a compact RL loop suitable for training or evaluation.

## Environment Summary

- Domain: guided Python coding workspace
- API: OpenEnv `reset()` / `step()` / `state()`
- Interaction style: multi-step, test-driven
- Evaluation: deterministic execution-based grading
- Deployment target: Hugging Face Space with Docker
- Client mode: WebSocket

## Task Families

CodeReviewEnv currently ships with local template families that generate
deterministic workspace variants from a task id and seed.

| Difficulty | Families | Shape |
| --- | --- | --- |
| Easy | implementation, repair | one file, one function, 1-2 public tests |
| Medium | implementation, repair | one module or class, 2-3 public tests |
| Hard | integration, repair | 2-3 files, integration behavior, 3 public tests |

Current seed templates:

- `easy_implementation_discount`
- `easy_repair_slugify`
- `medium_implementation_inventory`
- `medium_repair_budget`
- `hard_integration_orders`
- `hard_repair_auth`

Each episode is generated locally from:

- a deterministic workspace
- editable file constraints
- public tests
- hidden tests
- a task brief
- a fixed step budget and test budget

## Core Loop

Each episode works like this:

1. `reset()` returns a task brief and the initial workspace snapshot.
2. The agent may inspect files with `read_files`.
3. The agent edits workspace files with `update_files`.
4. The agent calls `run_tests`.
5. The environment returns:
   - public test progress
   - structured failure details
   - stdout, stderr, and exit code
   - reward
6. The loop continues until hidden tests pass or the budgets are exhausted.

This is intended to teach agents to improve code through execution feedback, not
to guess a stored answer.

## Reward Design

Reward is issued mainly on `run_tests`.

- `read_files`: `0.0`
- `update_files`: `0.0`
- `run_tests`: shaped reward in `[0.0, 1.0]`

Current `run_tests` formula:

- `0.40 * public_test_pass_ratio`
- `0.25 * hidden_test_pass_ratio` once hidden tests are checked
- `0.15 * deterministic_quality_score`
- `0.10 * module_load_validity`
- `0.10 * execution_efficiency` based on remaining step and test budget

Additional reward penalties:

- no-op file updates reduce the next `run_tests` reward
- rerunning tests without changing the workspace reduces the next `run_tests` reward
- invalid update attempts accumulate a small penalty for the next test run

The deterministic quality score checks:

- editable files parse as valid Python
- no `eval()` or `exec()`
- no wildcard imports
- no top-level debug `print()` calls

Hidden tests are checked once public tests pass or on the final allowed test
run. Success requires hidden tests to pass. A solved episode can still score
below `1.0` if it uses extra actions or test runs, which keeps the baseline
more realistic than a binary all-or-nothing benchmark.

Budgets:

- `max_test_runs`: easy `3`, medium `4`, hard `4`
- `max_steps`: easy `8`, medium `12`, hard `14`

## Action Space

`ReviewAction` exposes explicit workspace tools:

- `action_type`
  one of `read_files`, `update_files`, `run_tests`
- `paths`
  file paths to read when using `read_files`
- `files`
  path-to-full-content map when using `update_files`
- `summary`
  optional short note describing the change

Example:

```python
ReviewAction(
    action_type="update_files",
    files={
        "pricing.py": "def apply_discount(subtotal, has_coupon):\n    ...\n",
    },
    summary="Implement the coupon rule and round to 2 decimals.",
)
```

## Observation Space

`ReviewObservation` contains:

- `solved`
- `task_brief`
- `workspace_files`
- `stdout`
- `stderr`
- `exit_code`
- `feedback`
- `failing_tests`
- `failure_details`
- `task_id`
- `difficulty`
- `tests_passed`
- `tests_total`
- `test_runs_used`
- `max_test_runs`
- `reward`
- `done`

Observations are structured so an agent can use them programmatically rather
than relying only on prose.

## State Space

`ReviewState` contains:

- `episode_id`
- `step_count`
- `difficulty`
- `best_score`
- `solved`
- `tests_passed`
- `tests_total`
- `test_runs_used`
- `max_test_runs`
- `task_id`
- `workspace_manifest`

## Repository Layout

- [tasks.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/tasks.py)
  task descriptors, seeded workspace generation, and task metadata
- [graders.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/graders.py)
  deterministic execution harness and reward computation
- [models.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/models.py)
  typed action, observation, and state models
- [server/environment.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/server/environment.py)
  main environment loop
- [client.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/client.py)
  WebSocket client
- [trl_env.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/trl_env.py)
  TRL tool wrapper
- [inference.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/inference.py)
  reproducible baseline runner
- [smoke_test.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/smoke_test.py)
  local sanity test

## Built-in UI and Routes

The server exposes the default OpenEnv UI and API routes:

- `/web/` interactive Gradio UI
- `/docs` Swagger UI
- `/redoc` ReDoc
- `/health` health check
- `/schema` environment schema
- `/reset` start an episode
- `/step` send an action
- `/state` inspect state
- `/ws` WebSocket endpoint

`/` redirects to `/web/` when the web interface is enabled.

## Stateful API Note

- `/reset` is easy to test over plain HTTP.
- `/step` is stateful and should be tested via `/web/` or the Python/WebSocket client.
- One-off `curl` calls to `/step` are not a reliable manual test because they do
  not preserve session state across the episode.

## Run Locally

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

## Quick Smoke Test

With the server running:

```bash
python smoke_test.py
```

The smoke test:

1. resets to a known easy task
2. applies an intentionally incomplete update
3. runs tests and checks partial reward
4. applies a corrected update
5. runs tests again and checks the solved state

## Python Client Example

```python
from code_review_env import CodeReviewEnv, ReviewAction

client = CodeReviewEnv(base_url="http://localhost:7860").sync()

with client:
    reset_result = client.reset(difficulty="easy")
    observation = reset_result.observation
    print(observation.task_brief)
    print(observation.workspace_files)

    client.step(
        ReviewAction(
            action_type="update_files",
            files={
                "pricing.py": "def apply_discount(subtotal, has_coupon):\n    return round(subtotal, 2)\n",
            },
            summary="First implementation pass.",
        )
    )

    test_result = client.step(ReviewAction(action_type="run_tests"))
    print(test_result.reward)
    print(test_result.observation.feedback)
```

## TRL Tool Wrapper

[trl_env.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/trl_env.py) exposes exactly two tool methods for `GRPOTrainer(environment_factory=CodeReviewToolEnv)`:

- `update_files(files: dict[str, str], summary: str = "")`
- `run_tests()`

The initial workspace snapshot is included in `reset()`, so `read_files` is not
required in the TRL wrapper.

## Baseline Inference

[inference.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/inference.py) is submission-compliant:

- root-level file
- OpenAI Python client only
- reads `API_BASE_URL`, `MODEL_NAME`, and `HF_TOKEN`
- emits exact `[START]`, `[STEP]`, `[END]` lines
- writes `results.json`

Environment variables used by [inference.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/inference.py):

- `HF_TOKEN`
  required secret used as the `api_key` for the OpenAI-compatible client
- `API_BASE_URL`
  optional endpoint override, defaults to `https://router.huggingface.co/v1`
- `MODEL_NAME`
  optional model id override, defaults to `Qwen/Qwen2.5-72B-Instruct`

How to get them:

1. `HF_TOKEN`
   create a Hugging Face access token at `https://huggingface.co/settings/tokens`
2. `API_BASE_URL`
   use `https://router.huggingface.co/v1` for the Hugging Face router unless you are pointing to another OpenAI-compatible provider
3. `MODEL_NAME`
   choose the model id you want to evaluate, for example `Qwen/Qwen2.5-72B-Instruct`

How the code uses them:

```python
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN,
)
```

Run:

```bash
export HF_TOKEN=...
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
python inference.py --url http://localhost:7860 --episodes 6 --seed 42
```

## Baseline Scores

Current committed local baseline from:

```bash
python inference.py --url http://localhost:7860 --episodes 18 --seed 42
```

using:

- `API_BASE_URL=https://router.huggingface.co/v1`
- `MODEL_NAME=Qwen/Qwen2.5-72B-Instruct`

Results:

- mean score: `0.9377`
- std score: `0.1429`
- easy mean: `0.9708`
- medium mean: `0.9792`
- hard mean: `0.8630`

These numbers are recorded in [results.json](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/results.json).
If you switch models or endpoints, rerun [inference.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/inference.py)
to refresh the baseline for that configuration.

## Manual API Testing

Reset:

```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"difficulty":"easy"}'
```

State:

```bash
curl http://localhost:7860/state
```

## Operator Checklist

Before submission:

1. run `openenv validate`
2. run `python -m compileall .`
3. run `python smoke_test.py`
4. run `docker build .`
5. run the final baseline inference
6. verify the Hugging Face Space is `Running`
7. stop unnecessary Spaces before submitting

You can also run the bundled validator:

```bash
chmod +x scripts/validate-submission.sh
./scripts/validate-submission.sh https://your-space.hf.space .
```

## Current Limitations

- Task families are local templates rather than external benchmark integrations.
- The workspace is guided and bounded by editable files; it is not a full shell or arbitrary REPL.
