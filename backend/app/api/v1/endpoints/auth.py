from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUserID, DBSession
from app.repositories.user_repository import UserRepository
from app.schemas.user import LoginRequest, RefreshTokenRequest, TokenResponse, UserCreate, UserUpdate, UserResponse, ChangePasswordRequest
from app.services.auth_service import AuthService
from app.core.security import hash_password, verify_password

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: UserCreate, db: DBSession) -> UserResponse:
    """Register a new user account."""
    service = AuthService(db)
    user = await service.register(payload)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DBSession) -> TokenResponse:
    """Authenticate and receive access + refresh tokens."""
    service = AuthService(db)
    return await service.login(payload.email, payload.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshTokenRequest, db: DBSession) -> TokenResponse:
    """Exchange a valid refresh token for a new token pair."""
    service = AuthService(db)
    return await service.refresh(payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(user_id: CurrentUserID, db: DBSession) -> UserResponse:
    """Return the currently authenticated user's profile."""
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)  # type: ignore[arg-type]
    if not user:
        from app.core.exceptions import UnauthorizedError
        raise UnauthorizedError("User not found")
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_me(payload: UserUpdate, user_id: CurrentUserID, db: DBSession) -> UserResponse:
    """Update the authenticated user's profile (full_name)."""
    from fastapi import HTTPException
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)  # type: ignore[arg-type]
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name

    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/me/change-password", status_code=200)
async def change_password(
    payload: ChangePasswordRequest,
    user_id: CurrentUserID,
    db: DBSession,
) -> dict:
    """Change the authenticated user's password."""
    from fastapi import HTTPException
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)  # type: ignore[arg-type]
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.hashed_password = hash_password(payload.new_password)
    await db.commit()
    return {"message": "Password updated successfully"}
