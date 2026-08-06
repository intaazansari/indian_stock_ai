#!/bin/sh
set -e
exec python -m celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
