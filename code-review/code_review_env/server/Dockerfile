FROM python:3.10-slim

WORKDIR /app

# Create non-root user
RUN useradd -m appuser

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn openenv

# Copy code
COPY . .

# Adjust permissions
RUN chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PORT=7860
ENV PYTHONPATH=/app

# Expose port
EXPOSE 7860

# Run server
# Note: entrypoint relative to PYTHONPATH
CMD uvicorn code_review_env.server.app:app --host 0.0.0.0 --port $PORT
