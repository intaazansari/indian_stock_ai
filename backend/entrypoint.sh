#!/bin/sh
# Render free instances have 512 MB RAM and a fraction of a CPU, and every
# wake-from-sleep re-runs this script. Keep startup light and resilient:
#   - Retry migrations (Neon may be cold-starting) instead of crashing the
#     container, which leaves Render answering 503 until the next deploy.
#   - Run a single uvicorn worker by default (each worker loads ~150 MB).

attempt=1
max_attempts="${MIGRATION_MAX_ATTEMPTS:-5}"
until python -m alembic upgrade head; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "WARNING: alembic upgrade failed after $attempt attempts; starting API anyway" >&2
    break
  fi
  echo "alembic upgrade failed (attempt $attempt/$max_attempts); retrying in $((attempt * 5))s" >&2
  sleep $((attempt * 5))
  attempt=$((attempt + 1))
done

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_CONCURRENCY:-1}"
