"""任务模型"""
from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
import enum

from filmdub.core.database import Base


class JobStatus(str, enum.Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    """任务模型"""
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 任务配置
    module_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # 状态
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 进度
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # 关系
    project: Mapped["Project"] = relationship(back_populates="jobs")

    @property
    def user_friendly_status(self) -> str:
        """用户友好的状态描述"""
        status_map = {
            JobStatus.PENDING: "等待中",
            JobStatus.RUNNING: "运行中",
            JobStatus.COMPLETED: "已完成",
            JobStatus.FAILED: "失败",
            JobStatus.CANCELLED: "已取消",
        }
        return status_map.get(self.status, self.status)

    @property
    def user_friendly_error(self) -> str | None:
        """用户友好的错误信息"""
        return self.error_message if self.status == JobStatus.FAILED else None
