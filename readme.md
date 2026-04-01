# OpenEnv

This repo contains a production-style OpenEnv environment for drug interaction reasoning.

## Run Locally

1. Enter the project:

```bash
cd drug_interaction_env
```

2. Install dependencies in your active environment:

```bash
pip install -e ".[dev,server]"
```

3. Create a `.env` file for OpenRouter:

```bash
cat > .env <<'EOF'
OPENAI_API_KEY=your_openrouter_key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_HTTP_REFERER=https://your-site.example
OPENROUTER_X_TITLE=Drug-Interaction-Env
EOF
```

4. Start the environment server in one terminal:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

5. Run the benchmark in another terminal:

```bash
python inference.py --url http://localhost:8000 --episodes 20 --seed 42
```

6. Run tests:

```bash
pytest
```

## Notes

- The default model is `nvidia/nemotron-3-super-120b-a12b:free`.
- Free OpenRouter endpoints are logged and should not be used for sensitive or production traffic.
- Results are written to `drug_interaction_env/results.json`.

Detailed environment docs are in [drug_interaction_env/README.md](/Users/harsh/Desktop/gitRepos/openenv/drug_interaction_env/README.md).
