"""
Custom exception hierarchy.

Rules:
  - Every domain error has a specific exception class.
  - Never raise raw HTTP exceptions in service or repository layers.
  - The API layer converts domain exceptions to HTTP responses.
  - Never leak internal error details to the client in production.
"""
from __future__ import annotations

from fastapi import status


class ApplicationError(Exception):
    """Base exception for all application-level errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


# ── 400 Bad Request ───────────────────────────────────────────────────────────
class ValidationError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Validation error"


class InvalidInputError(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Invalid input"


# ── 401 Unauthorized ──────────────────────────────────────────────────────────
class UnauthorizedError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Authentication required"


class InvalidCredentialsError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Invalid email or password"


class TokenExpiredError(ApplicationError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Token has expired"


# ── 403 Forbidden ─────────────────────────────────────────────────────────────
class ForbiddenError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Access denied"


# ── 404 Not Found ─────────────────────────────────────────────────────────────
class NotFoundError(ApplicationError):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found"


class CompanyNotFoundError(NotFoundError):
    detail = "Company not found"


class UserNotFoundError(NotFoundError):
    detail = "User not found"


# ── 409 Conflict ──────────────────────────────────────────────────────────────
class ConflictError(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource already exists"


class UserAlreadyExistsError(ConflictError):
    detail = "A user with this email already exists"


# ── 429 Too Many Requests ─────────────────────────────────────────────────────
class RateLimitExceededError(ApplicationError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    detail = "Rate limit exceeded. Please slow down."


class AIRateLimitExceededError(RateLimitExceededError):
    detail = "AI analysis rate limit exceeded. Try again later."


# ── 502 Bad Gateway ───────────────────────────────────────────────────────────
class ExternalServiceError(ApplicationError):
    status_code = status.HTTP_502_BAD_GATEWAY
    detail = "External service unavailable"


class DataSourceError(ExternalServiceError):
    detail = "Financial data source is currently unavailable"


class AIServiceError(ExternalServiceError):
    detail = "AI service is currently unavailable"
