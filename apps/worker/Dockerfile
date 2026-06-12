# PhoneWala Gyan worker — FastAPI internal API + job consumers
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# uv for fast, reproducible installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install deps first for layer caching. google-genai = STACK_TIER=free LLM provider.
# (bge-m3/torch stays out of the image — free runs use mock embeddings; add the
# `embeddings` extra when deploying real BGE-M3.)
COPY apps/worker/pyproject.toml ./
RUN uv pip install --system -r pyproject.toml google-genai

COPY apps/worker/app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
