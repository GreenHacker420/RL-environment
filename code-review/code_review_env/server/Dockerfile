FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 7860

CMD sh -c "uvicorn code_review_env.server.app:app --host 0.0.0.0 --port ${PORT:-7860}"
