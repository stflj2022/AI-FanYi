"""人物模型"""
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime

from filmdub.core.database import Base


class Character(Base):
    """人物模型"""
    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 人物属性
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    age_range: Mapped[str | None] = mapped_column(String(50), nullable=True)
    role_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    actor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 头像
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 首次出现
    first_appearance_episode_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # 关系
    project: Mapped["Project"] = relationship(back_populates="characters")
