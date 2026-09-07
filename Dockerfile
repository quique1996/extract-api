# Extract API — multi-stage Docker image.
#
# The inference backend (Ollama + `ornith-1.5:9b`) is NOT committed here. In CI the
# image is built then run as a plain app container (see CI runner `docker` job:
# `docker run -p 8100:8100`). To run the full stack locally with Ollama
# inference you ship `docker-compose.yml` which mounts the host Ollama over the
# network and shares a model layer — see Docker/README for env vars.
#
# Build:
#   docker build -f Dockerfile -t extract-api:latest .
#
# Run (expects an Ollama /v1 reachable at LLM_BASE_URL and the model):
#   docker run --rm -p 8100:8100 \
#     -e LLM_BASE_URL=${LLM_BASE_URL:-} \
#     -e LLM_MODEL=${LLM_MODEL:-ornith-1.5:9b} \
#     extract-api:latest
#
# Test:
#   docker run --rm -v "$PWD/tests:/app/tests" -t extract-api:latest sh -c "cd /app && pip install pytest && python -m pytest -q"

FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

# System deps needed for uvicorn (openssl runtime).
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt || \
    pip install --no-cache-dir -r requirements.txt

# Build-arg used by uvicorn for graceful shutdown.
ARG UVICORN_PROXY_FIX

COPY main.py /app/main.py
COPY Pyproject.toml /app/Pyproject.toml

# Uvicorn worker for async /extract/batch (asyncio.gather).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8100"]
