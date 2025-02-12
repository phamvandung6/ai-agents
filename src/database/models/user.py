from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.models.base import Base


class User(Base):
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password: Mapped[str]
    role: Mapped[str] = mapped_column(String(50), default="user")
    is_active: Mapped[bool] = mapped_column(default=True)
