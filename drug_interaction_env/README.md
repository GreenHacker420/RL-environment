---
title: Drug Interaction Env
sdk: docker
app_port: 7860
---

# Drug Interaction Env

Drug Interaction Env is an OpenEnv-compatible FastAPI microservice for benchmarking and training LLM agents on clinically realistic drug-drug interaction reasoning. The environment is fully self-contained, uses typed action/observation/state models, and returns dense rewards that account for safety, correctness, and explanation quality.

It includes three task tiers: single pair classification, medication list review, and full patient triage. The included `inference.py` script can benchmark an OpenAI model or fall back to a deterministic dummy agent when no API key is configured.

## Installation

```bash
cd drug_interaction_env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,server]"
```

## Quickstart

Start the environment locally:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

Run the tests:

```bash
pytest
```

## Environment API

The environment follows the OpenEnv pattern of `reset()`, `step()`, and `state`.

```python
from server.environment import DrugInteractionEnv
from models import DrugAction

env = DrugInteractionEnv()
observation = env.reset()
print(observation.prompt)

result = env.step(
    DrugAction(
        severity="severe",
        explanation="Bleeding risk is increased because of additive anticoagulant effects.",
    )
)
print(result.reward, result.feedback)
print(env.state)
```

Client usage over the service:

```python
import asyncio
from client import DrugEnvClient
from models import DrugAction

async def main() -> None:
    async with DrugEnvClient(base_url="http://localhost:8000") as client:
        reset_result = await client.reset()
        action = DrugAction(
            severity="moderate",
            explanation="Possible CYP-mediated interaction with monitoring required.",
        )
        step_result = await client.step(action)
        print(step_result.reward, step_result.observation.feedback)

asyncio.run(main())
```

## Task Types

- `easy`: classify the severity of a single drug pair and explain the mechanism.
- `medium`: analyze a 4-5 drug medication list and identify all clinically significant interacting pairs.
- `hard`: review a full patient case, choose triage level, identify the critical interaction, and recommend a medication change.

## Grading Rubric

- Easy tasks reward exact severity, near-miss severity, and explanation keyword coverage.
- Medium tasks normalize pair-level accuracy, penalize hallucinated interactions, and penalize missed true interactions.
- Hard tasks reward triage accuracy, identification of the critical pair, medication change advice, and explanation keywords.
- Safety penalties are explicit:
  - Reporting `none` for a non-none easy interaction returns `0.0`.
  - Reporting `normal` triage for an `emergency` hard case collapses the score to 10% of its pre-penalty value.

## Docker

Build the image:

```bash
docker build -t drug-interaction-env -f server/Dockerfile .
```

Run the container:

```bash
docker run --rm -p 7860:7860 drug-interaction-env
```

## Benchmarking

Example benchmark run:

```bash
python inference.py --url http://localhost:8000 --episodes 60 --seed 42 --model gpt-4o-mini
```

This writes `results.json` in the project root and prints a summary table with mean score, quantiles, and safety violations.

## Manifest

The OpenEnv manifest is defined in [openenv.yaml](/Users/harsh/Desktop/gitRepos/openenv/drug_interaction_env/openenv.yaml).
