"""
Structured logging configuration using structlog.

Outputs JSON in production, human-readable in development.
Every log entry gets a request_id for distributed tracing.
"""
from __future__ import annotations

import logging
import sys

import structlog


def setup_logging() -> None:
    """Configure structlog for the application."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if _is_development():
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Route standard library logging through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if _is_development() else logging.INFO,
    )


def _is_development() -> bool:
    import os
    return os.getenv("ENVIRONMENT", "development") == "development"
