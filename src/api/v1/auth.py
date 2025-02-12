from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import verify_token
from src.database import get_session
from src.database.models import User
from src.schema.auth import Token, UserCreate, UserLogin, UserResponse
from src.service.auth import AuthService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Register new user."""
    auth_service = AuthService(session)
    user = await auth_service.create_user(user_data)
    return auth_service.get_user_response(user)


@router.post("/login", response_model=Token)
async def login(
    form_data: UserLogin,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Login user."""
    auth_service = AuthService(session)
    token = await auth_service.authenticate(form_data)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Refresh access token."""
    auth_service = AuthService(session)
    return await auth_service.refresh_token(refresh_token)


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: Annotated[User, Depends(verify_token)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Get current user info."""
    auth_service = AuthService(session)
    return auth_service.get_user_response(current_user)
