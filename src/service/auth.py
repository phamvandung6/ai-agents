from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import (
    ALGORITHM,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from src.core.settings import settings
from src.database.models import User
from src.schema.auth import Token, TokenPayload, UserCreate, UserLogin, UserResponse


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if user exists
        existing_user = await self._get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create new user
        hashed_password = get_password_hash(user_data.password)
        user = User(email=user_data.email, password=hashed_password, is_active=True, role="user")
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate(self, form_data: UserLogin) -> Token | None:
        """Authenticate user and return tokens."""
        user = await self._get_user_by_email(form_data.email)
        if not user or not verify_password(form_data.password, user.password):
            return None

        return Token(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def refresh_token(self, user_id: str) -> Token:
        """Create new token pair."""
        return Token(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),
        )

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID."""
        query = await self.session.execute(select(User).where(User.id == user_id))
        return query.scalar_one_or_none()

    async def _get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        query = await self.session.execute(select(User).where(User.email == email))
        return query.scalar_one_or_none()

    def get_user_response(self, user: User) -> UserResponse:
        """Convert User model to UserResponse schema."""
        return UserResponse(email=user.email, is_active=user.is_active, role=user.role)

    async def verify_token(self, token: str) -> User | None:
        """Verify JWT token and return user if valid."""
        try:
            payload = jwt.decode(
                token,
                settings.AUTH_SECRET.get_secret_value(),
                algorithms=[ALGORITHM],
            )
            token_data = TokenPayload(**payload)

            if token_data.sub is None:
                return None

            if token_data.type != "access":
                return None

            user = await self._get_user_by_id(token_data.sub)
            return user

        except JWTError:
            return None

    async def _get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID."""
        query = await self.session.execute(
            select(User).where(User.id == user_id),
        )
        return query.scalar_one_or_none()
