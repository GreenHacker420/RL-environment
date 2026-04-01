FROM python:3.11-slim
RUN useradd -m appuser
WORKDIR /app
COPY --chown=appuser:appuser . .
RUN pip install --no-cache-dir -e ".[server]"
USER appuser
ENV PORT=7860 HOST=0.0.0.0 WORKERS=2
CMD uvicorn server.app:app --host $HOST --port $PORT --workers $WORKERS
