---
title: Drug Interaction Env
sdk: docker
app_port: 7860
---

# Drug Interaction Env

Drug Interaction Env is an OpenEnv-style FastAPI microservice for benchmarking and training LLM agents on clinically realistic drug-drug interaction reasoning. It is self-contained at runtime, uses typed action/observation/state models, and returns dense rewards that reflect clinical correctness, explanation quality, and safety.

The environment includes three task tiers: single-pair severity classification, multi-drug medication review, and full patient triage. It can be benchmarked with `inference.py` using an OpenAI-compatible API endpoint or a deterministic dummy agent when no API key is set.

This repo now targets the installed OpenEnv runtime directly via `openenv.core.*` imports rather than a local compatibility shim.

## Installation

```bash
cd drug_interaction_env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,server]"
```

## Quickstart

Start the service:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

Run tests:

```bash
pytest
```

Run a smoke benchmark with the deterministic dummy agent:

```bash
python inference.py --url http://localhost:8000 --episodes 5 --seed 42
```

## Environment API

The environment exposes the standard `reset()`, `step()`, and `state` interface.

```python
from server.environment import DrugInteractionEnv
from models import DrugAction

env = DrugInteractionEnv()
observation = env.reset(seed=42)
print(observation.prompt)

result = env.step(
    DrugAction(
        severity="severe",
        explanation="Additive anticoagulant effects increase bleeding risk.",
    )
)
print(result.reward, result.feedback)
print(env.state)
```

Client usage:

```python
from client import DrugEnvClient
from models import DrugAction

with DrugEnvClient(base_url="http://localhost:8000").sync() as client:
    reset_result = client.reset()
    step_result = client.step(
        DrugAction(
            severity="moderate",
            explanation="Clinically important interaction requiring monitoring.",
        )
    )
    print(step_result.reward)
```

Under the hood, `DrugEnvClient` subclasses `openenv.core.env_client.EnvClient`, so benchmarking uses the standard OpenEnv WebSocket session flow.

## Task Types

- `easy`: classify the severity of a single drug pair and explain the mechanism.
- `medium`: analyze a 4-5 drug medication list and identify all clinically significant interacting pairs.
- `hard`: review a full patient case, choose triage level, identify the critical interaction, and recommend a medication change.

## Grading Summary

- Easy tasks reward exact severity, near-miss severity, and explanation keyword coverage.
- Medium tasks award pair-level partial credit and penalize missed or hallucinated interactions.
- Hard tasks reward triage accuracy, critical interaction identification, medication change advice, and explanation keywords.
- Safety rules are explicit:
  - Predicting `none` for a true non-none easy interaction returns `0.0`.
  - Predicting `normal` for an emergency hard case applies a severe score collapse.

## Docker

Build:

```bash
docker build -t drug-interaction-env -f server/Dockerfile .
```

Run:

```bash
docker run --rm -p 7860:7860 drug-interaction-env
```

## Benchmarking

Default benchmark command:

```bash
python inference.py --url http://localhost:8000 --episodes 60 --seed 42
```

This writes `results.json` and prints a summary table with mean score, spread, and safety violations.

### Free Model Options

This repo now defaults to the OpenRouter free model you selected:

- `nvidia/nemotron-3-super-120b-a12b:free`

Use it only for trial evaluation. OpenRouter marks free endpoints as logged, non-confidential, and not suitable for production or business-critical systems.

Example:

```bash
export OPENAI_API_KEY=your_openrouter_key
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export OPENROUTER_HTTP_REFERER=https://your-site.example
export OPENROUTER_X_TITLE=Drug-Interaction-Env
python inference.py \
  --url http://localhost:8000 \
  --episodes 20 \
  --seed 42
```

If you want to override the default model explicitly:

```bash
python inference.py \
  --url http://localhost:8000 \
  --episodes 20 \
  --seed 42 \
  --model nvidia/nemotron-3-super-120b-a12b:free
```

If you do not set `OPENAI_API_KEY`, `inference.py` falls back to the deterministic dummy agent, which is useful for reproducible smoke tests and CI.

## Verification Performed In This Workspace

The following were run locally in this checkout:

- `python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"`
- `pytest`
- `python inference.py --url http://127.0.0.1:8000 --episodes 3 --seed 42`

The benchmark smoke test above ran without `OPENAI_API_KEY`, so it used the deterministic dummy agent. That path is now verified end to end and produced a `results.json` file in the project root.

`docker build` was not fully verified in this session because the local Docker CLI could not reach a running daemon. The Dockerfile and local Uvicorn deployment path are in place.

## Manifest

The OpenEnv manifest is defined in [openenv.yaml](/Users/harsh/Desktop/gitRepos/openenv/drug_interaction_env/openenv.yaml).
