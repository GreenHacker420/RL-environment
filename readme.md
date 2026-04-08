# OpenEnv Workspace

This repository now centers on the hackathon submission in
[code-review/code_review_env](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env).

## Main Project

- [code-review/code_review_env/README.md](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/README.md)
  full environment documentation
- [code-review/code_review_env/openenv.yaml](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/openenv.yaml)
  OpenEnv metadata
- [code-review/code_review_env/inference.py](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/inference.py)
  baseline runner
- [code-review/code_review_env/Dockerfile](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/Dockerfile)
  deployment image used for local validation and HF Spaces

## What It Contains

The submission project is a guided Python coding workspace built with OpenEnv.
An agent:

1. inspects a workspace manifest
2. reads files explicitly
3. updates code
4. runs lint and tests
5. improves code over multiple steps using structured feedback

## Repo Layout

```text
openenv/
├── code-review/
│   └── code_review_env/
│       └── ... hackathon submission ...
├── docs/
│   └── ... local reference notes ...
└── readme.md
```

## Quick Start

```bash
cd code-review/code_review_env
openenv validate
python server/app.py
```

Then open:

- `http://localhost:7860/web/`
- `http://localhost:7860/docs`

## Validation

From the submission project root:

```bash
python smoke_test.py
docker build -t code-review-env .
python inference.py --url http://localhost:7860 --episodes 27 --seed 42
```

For the full submission checklist and benchmark details, use the project README:

- [code-review/code_review_env/README.md](/Users/harsh/Desktop/gitRepos/openenv/code-review/code_review_env/README.md)
