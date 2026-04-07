# CodeReviewEnv

CodeReviewEnv is a small OpenEnv benchmark where an agent reviews buggy Python code,
identifies bug locations, classifies bug types, and submits corrected code.

This project does not include a custom frontend. The UI you get by default comes
from OpenEnv/FastAPI:

- Swagger UI at `http://localhost:7860/docs`
- ReDoc at `http://localhost:7860/redoc`
- OpenAPI schema at `http://localhost:7860/openapi.json`

If you want a custom browser UI for playing with tasks, that would need to be
built separately. Out of the box, OpenEnv gives you the API server, the docs UI,
and the WebSocket environment session endpoint.

The task set is fully hardcoded in `tasks.py`:

- 5 easy tasks with one bug each
- 4 medium tasks with one class and two bugs each
- 3 hard tasks with two modules and three bugs each

## Run locally

From the environment root:

```bash
openenv validate
python server/app.py
python inference.py --url http://localhost:7860 --episodes 12 --seed 42
```

After the server starts, open:

- `http://localhost:7860/docs` for the interactive Swagger UI
- `http://localhost:7860/redoc` for the static API docs

## What the built-in UI does

The built-in Swagger UI lets you:

- inspect the request and response schemas
- manually call `/reset`, `/step`, `/state`, `/health`, and `/schema`
- verify the observation and action payloads without writing a client first

It is useful for debugging the environment API, but it is not a task-specific
visual interface for code review episodes.

## Main routes

These routes are exposed by the server:

- `GET /docs`
  Opens Swagger UI.
- `GET /redoc`
  Opens ReDoc documentation.
- `GET /openapi.json`
  Returns the OpenAPI schema for the server.
- `GET /health`
  Simple health check. Returns `{"status":"healthy"}` when the server is up.
- `GET /metadata`
  Returns basic environment metadata.
- `GET /schema`
  Returns the JSON schemas for the action, observation, and state models.
- `GET /state`
  Returns the current environment state for the active session context.
- `POST /reset`
  Starts a new episode and returns the initial observation. For this project,
  that observation contains the buggy code prompt and task metadata.
- `POST /step`
  Submits a `ReviewAction` and returns the graded result. This environment is
  single-step, so one `step` completes the episode.
- `WS /ws`
  Persistent WebSocket endpoint used by the OpenEnv client. This is the main
  route used by `client.py`, `trl_env.py`, and `inference.py`.
- `POST /mcp`
  MCP JSON-RPC endpoint.
- `WS /mcp`
  MCP WebSocket endpoint.

## How this environment behaves

Each episode is exactly:

1. `reset()`
2. one `step(action)`
3. done

`reset()` chooses one random task from the selected difficulty tier and returns
the buggy code as the prompt.

`step()` grades the submitted action:

- easy tasks use `grade_easy`
- medium tasks use `grade_medium`
- hard tasks use `grade_hard`

The returned observation includes:

- `done`
- `reward`
- `feedback`
- `task_id`
- `difficulty`

## How to use the API manually

Example reset request:

```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"difficulty":"easy"}'
```

Example step request:

```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "bug_line": 2,
      "bug_type": "wrong operator",
      "description": "comparison operator age",
      "fixed_code": "def is_adult(age):\n    return age >= 18",
      "metadata": {}
    }
  }'
```

For normal use, prefer the provided Python client in `client.py`, which talks to
the server over WebSocket.

## Project files

- `tasks.py`
  Hardcoded benchmark tasks.
- `models.py`
  `ReviewAction`, `ReviewObservation`, and `ReviewState`.
- `graders.py`
  Scoring logic for easy, medium, and hard tasks.
- `server/environment.py`
  Single-step OpenEnv environment implementation.
- `server/app.py`
  FastAPI app wiring.
- `client.py`
  WebSocket client for the environment.
- `trl_env.py`
  TRL/GRPO-compatible tool environment wrapper.
- `inference.py`
  End-to-end evaluation script that writes `results.json`.
