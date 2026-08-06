"""
Celery application configuration.

Three queues:
  - default       → general tasks
  - ai_analysis   → AI agent tasks (can be scaled separately)
  - data_sync     → NSE/BSE data ingestion tasks
"""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

# Celery is optional — only initialise when a broker is configured.
# In dev (no Redis/RabbitMQ), CELERY_BROKER_URL is empty and workers simply
# won't start; the API continues to work fine without background tasks.
if settings.CELERY_BROKER_URL:
    celery_app = Celery(
        "stocksage",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=[
            "app.workers.tasks.data_sync",
            "app.workers.tasks.ai_analysis",
            "app.workers.tasks.report_ingestion",
        ],
    )
else:
    celery_app = Celery("stocksage")   # no-op shell — tasks registered but never dispatched

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,                    # Safer: ack only after completion
    worker_prefetch_multiplier=1,           # One task at a time per worker
    task_routes={
        "app.workers.tasks.ai_analysis.*": {"queue": "ai_analysis"},
        "app.workers.tasks.data_sync.*": {"queue": "data_sync"},
        "app.workers.tasks.report_ingestion.*": {"queue": "default"},
    },
    beat_schedule={
        # Run every day at 8 PM IST (after market close)
        "sync-market-data-daily": {
            "task": "app.workers.tasks.data_sync.sync_all_companies",
            "schedule": 60 * 60 * 24,       # Every 24 hours
            "options": {"queue": "data_sync"},
        },
        # Trigger AI analysis refresh for stale cache entries
        "refresh-stale-analysis": {
            "task": "app.workers.tasks.ai_analysis.refresh_stale_analysis_cache",
            "schedule": 60 * 60 * 6,        # Every 6 hours
            "options": {"queue": "ai_analysis"},
        },
    },
)
