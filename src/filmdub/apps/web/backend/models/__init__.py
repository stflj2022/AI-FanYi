"""Web Backend 数据库模型"""
from sqlalchemy import Boolean, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
import uuid
from datetime import datetime

from filmdub.core.database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default=lambda: {}, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )


# Import core models (re-export for convenience)
from filmdub.core.models import WebProject as Project, Job, Character

__all__ = ["User", "Project", "Job", "Character"]
