# ─────────────────────────────────────────────
# Backend Dockerfile
# Multi-stage: development + production targets
# ─────────────────────────────────────────────

# ── Base ──────────────────────────────────────
FROM python:3.13-slim AS base

WORKDIR /app

# System deps: psycopg2 needs libpq
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Development ───────────────────────────────
FROM base AS development

COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production ────────────────────────────────
FROM base AS production

COPY . .

# Create non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

# PORT is injected by Render (and other PaaS platforms). Default to 8000 for local runs.
ENV PORT=8000
EXPOSE $PORT

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# render.yaml overrides this CMD with: alembic upgrade head && uvicorn ...
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 2"]
