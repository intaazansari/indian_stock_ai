from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    get_subject_from_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import TokenResponse, UserCreate


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = UserRepository(session)

    async def register(self, payload: UserCreate) -> User:
        if await self.repo.email_exists(payload.email):
            raise UserAlreadyExistsError()

        user = await self.repo.create(
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.repo.get_by_email(email.lower())
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InvalidCredentialsError("Account is inactive")

        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        user_id = get_subject_from_token(refresh_token, expected_type=TokenType.REFRESH)
        # Verify user still exists and is active
        user = await self.repo.get_by_id(user_id)  # type: ignore[arg-type]
        if not user or not user.is_active:
            from app.core.exceptions import UnauthorizedError
            raise UnauthorizedError("User not found or inactive")

        return TokenResponse(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),
        )
