"""
Security utilities: JWT token management and password hashing.

Design decisions:
  - HS256 with a strong secret key for JWT (RS256 when scaling to microservices)
  - bcrypt for password hashing (cost factor 12)
  - Separate access tokens (short-lived) and refresh tokens (long-lived)
  - Tokens carry minimal claims — never embed sensitive user data
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a short-lived JWT access token."""
    return _create_token(
        subject=subject,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims=extra_claims,
    )


def create_refresh_token(subject: str) -> str:
    """Create a long-lived JWT refresh token."""
    return _create_token(
        subject=subject,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: TokenType = TokenType.ACCESS) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Raises UnauthorizedError for any invalid token scenario.
    Never expose the underlying JWTError to the client.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        token_type: str | None = payload.get("type")
        if token_type != expected_type:
            raise UnauthorizedError("Invalid token type")
        return payload
    except JWTError:
        raise UnauthorizedError("Could not validate credentials")


def get_subject_from_token(token: str, expected_type: TokenType = TokenType.ACCESS) -> str:
    payload = decode_token(token, expected_type)
    subject: str | None = payload.get("sub")
    if subject is None:
        raise UnauthorizedError("Token missing subject claim")
    return subject


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(tz=timezone.utc)
    claims: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
