#!/usr/bin/env bash
# build.sh — Render pre-start script for the backend service
#
# Render calls this via the dockerCommand in render.yaml:
#   bash -c "alembic upgrade head && uvicorn app.main:app ..."
#
# This standalone script is also useful for local Docker production runs:
#   docker run isa-backend bash build.sh
#
# What it does:
#   1. Wait for PostgreSQL to be ready (Render starts DB before web service,
#      but asyncpg connection may need a few seconds)
#   2. Run Alembic migrations (idempotent — safe to run on every deploy)
#   3. Exit 0 so the main process (uvicorn) starts

set -euo pipefail

echo "==> Running Alembic migrations..."
alembic upgrade head
echo "==> Migrations complete."
