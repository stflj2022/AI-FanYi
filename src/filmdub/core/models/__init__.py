"""
SQLAlchemy 数据模型

所有模型定义遵循 ADR 0002: Layer 0 数据库 Schema 设计
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from filmdub.core.database import Base


# ==================== 枚举类型 ====================

class ProjectStatus(str, PyEnum):
    """项目状态"""
    PENDING = "pending"
    INTAKE = "intake"
    PROCESSING = "processing"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class JobStatus(str, PyEnum):
    """作业状态"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class WorkflowType(str, PyEnum):
    """工作流类型"""
    SINGLE_EPISODE = "single_episode"
    BATCH_SEASON = "batch_season"
    BATCH_SERIES = "batch_series"
    CUSTOM = "custom"


class ArtifactType(str, PyEnum):
    """Artifact 类型"""
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    METADATA = "metadata"
    CHARACTER_DB = "character_db"
    VOICE_DB = "voice_db"
    DIALOGUE_TIMELINE = "dialogue_timeline"
    SCENE_TIMELINE = "scene_timeline"
    ANALYSIS_RESULT = "analysis_result"
    SYNTHESIS_CONFIG = "synthesis_config"
    FINAL_VIDEO = "final_video"
    QA_REPORT = "qa_report"
    ARCHIVE = "archive"
    LOG = "log"
    OTHER = "other"


class ArtifactStatus(str, PyEnum):
    """Artifact 状态"""
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


class WorkerStatus(str, PyEnum):
    """Worker 状态"""
    OFFLINE = "offline"
    IDLE = "idle"
    BUSY = "busy"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"


class WorkerType(str, PyEnum):
    """Worker 类型"""
    CPU = "cpu"
    GPU = "gpu"
    IO = "io"
    HYBRID = "hybrid"


class Gender(str, PyEnum):
    """性别"""
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    UNKNOWN = "unknown"


class AgeRange(str, PyEnum):
    """年龄段"""
    CHILD = "child"  # 0-12
    TEEN = "teen"  # 13-19
    YOUNG_ADULT = "young_adult"  # 20-35
    ADULT = "adult"  # 36-55
    SENIOR = "senior"  # 55+
    UNKNOWN = "unknown"


class RoleType(str, PyEnum):
    """角色类型"""
    MAIN = "main"
    SUPPORTING = "supporting"
    MINOR = "minor"
    CAMEO = "cameo"
    BACKGROUND = "background"
    UNKNOWN = "unknown"


# ==================== 模型定义 ====================

class ProjectRecord(Base):
    """项目表（Layer 0 orchestrator 专用，UUID 主键）

    注意：此模型与 ProjectM01（媒体摄入用、字符串主键）是两个不同概念。
    为避免同名遮蔽导致 SQLAlchemy 关系解析失败，此处命名为 ProjectRecord。
    """
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus),
        default=ProjectStatus.PENDING,
        nullable=False,
    )

    # 元数据
    media_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    season: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    episode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    original_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    target_language: Mapped[str] = mapped_column(String(10), default="zh-CN", nullable=False)

    # 外部数据源
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    imdb_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 用户
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)

    # 配置
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=True)

    # 关系
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="project", cascade="all, delete-orphan")
    characters: Mapped[list["Character"]] = relationship("Character", back_populates="project", cascade="all, delete-orphan")
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="project", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index("idx_project_status", "status"),
        Index("idx_project_tmdb", "tmdb_id"),
        Index("idx_project_created", "created_at"),
    )


class Job(Base):
    """作业表"""
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
    )

    # 执行信息
    module_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    worker_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("workers.id", ondelete="SET NULL"),
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # 依赖 (存储为 JSON 数组，兼容 SQLite 与 PostgreSQL)
    depends_on: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 输入输出 (存储为 JSON 数组，兼容 SQLite 与 PostgreSQL)
    input_artifacts: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    output_artifacts: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_stack: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 关系
    project: Mapped["ProjectRecord"] = relationship("ProjectRecord", back_populates="jobs")
    worker: Mapped[Optional["Worker"]] = relationship("Worker", back_populates="jobs")

    # 索引
    __table_args__ = (
        Index("idx_job_project", "project_id"),
        Index("idx_job_status", "status"),
        Index("idx_job_module", "module_id"),
        Index("idx_job_worker", "worker_id"),
    )


class Workflow(Base):
    """工作流表"""
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[WorkflowType] = mapped_column(
        Enum(WorkflowType),
        default=WorkflowType.SINGLE_EPISODE,
        nullable=False,
    )

    # 工作流定义 (DAG)
    definition: Mapped[dict] = mapped_column(JSON, nullable=False)

    # 版本控制
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 索引
    __table_args__ = (
        Index("idx_workflow_type", "type"),
        Index("idx_workflow_active", "is_active"),
    )


class Artifact(Base):
    """Artifact 表"""
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[ArtifactType] = mapped_column(
        Enum(ArtifactType),
        nullable=False,
    )
    status: Mapped[ArtifactStatus] = mapped_column(
        Enum(ArtifactStatus),
        default=ArtifactStatus.PENDING,
        nullable=False,
    )

    # 归属
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)
    module_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # 存储
    storage_type: Mapped[str] = mapped_column(String(20), default="minio", nullable=False)
    storage_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    storage_bucket: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 元数据
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSON, nullable=True)

    # 版本
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_artifact_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)

    # 引用计数
    ref_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关系
    project: Mapped[Optional["ProjectRecord"]] = relationship("ProjectRecord", back_populates="artifacts")

    # 索引
    __table_args__ = (
        Index("idx_artifact_project", "project_id"),
        Index("idx_artifact_job", "job_id"),
        Index("idx_artifact_type", "type"),
        Index("idx_artifact_status", "status"),
    )


class Worker(Base):
    """Worker 表"""
    __tablename__ = "workers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[WorkerStatus] = mapped_column(
        Enum(WorkerStatus),
        default=WorkerStatus.OFFLINE,
        nullable=False,
    )
    type: Mapped[WorkerType] = mapped_column(
        Enum(WorkerType),
        default=WorkerType.CPU,
        nullable=False,
    )

    # 能力
    capabilities: Mapped[dict] = mapped_column(JSON, nullable=True)

    # 资源
    cpu_cores: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    memory_gb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gpu_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gpu_memory_gb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 当前任务
    current_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)

    # 统计
    jobs_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_runtime_seconds: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # 心跳
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    heartbeat_interval_seconds: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # 位置
    host: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="worker")

    # 索引
    __table_args__ = (
        Index("idx_worker_status", "status"),
        Index("idx_worker_type", "type"),
        Index("idx_worker_heartbeat", "last_heartbeat"),
    )


class Character(Base):
    """人物表"""
    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 基本信息
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    aliases: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    # 属性
    gender: Mapped[Optional[Gender]] = mapped_column(Enum(Gender), nullable=True)
    age_range: Mapped[Optional[AgeRange]] = mapped_column(Enum(AgeRange), nullable=True)
    role_type: Mapped[Optional[RoleType]] = mapped_column(Enum(RoleType), nullable=True)

    # 演员信息
    actor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)

    # 描述
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personality: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    speech_pattern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 关系
    relationships: Mapped[dict] = mapped_column(JSON, nullable=True)

    # 首次出现
    first_appearance_season: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    first_appearance_episode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    first_appearance_timestamp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    voice_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    project: Mapped["ProjectRecord"] = relationship("ProjectRecord", back_populates="characters")

    # 索引
    __table_args__ = (
        Index("idx_character_project", "project_id"),
        Index("idx_character_actor", "actor_id"),
    )


class VoiceProfile(Base):
    """音色档案表"""
    __tablename__ = "voice_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)

    # 基本信息
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=True)

    # TTS 配置
    tts_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tts_model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tts_config: Mapped[dict] = mapped_column(JSON, nullable=True)

    # 声音特征 (参考值)
    pitch_range: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    speed_range: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    emotional_range: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    # 参考音频
    reference_audio_artifact_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 索引
    __table_args__ = (
        Index("idx_voice_profile_character", "character_id"),
        Index("idx_voice_profile_project", "project_id"),
    )


class ErrorLog(Base):
    """错误日志表"""
    __tablename__ = "error_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    error_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    error_code: Mapped[str] = mapped_column(String(50), nullable=False)
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    recoverability: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)

    # 上下文
    context: Mapped[dict] = mapped_column(JSON, nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 关联
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)
    worker_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)
    artifact_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)

    # 时间
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    first_occurrence: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # 处理
    is_handled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    handler: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 重试
    is_retryable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_error_log_timestamp", "timestamp"),
        Index("idx_error_log_job", "job_id"),
        Index("idx_error_log_project", "project_id"),
    )


# ==================== M01-M03 专用模型 ====================
# 这些模型使用字符串 ID，用于媒体摄入、研究和字幕处理


# 为测试兼容性创建别名（移到前面，避免关系解析错误）
# 注意：实际使用时这些别名指向 M01-M03 专用模型
class ProjectM01(Base):
    """项目信息（M01-M03 专用）"""
    __tablename__ = "m01_projects"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    target_language: Mapped[str] = mapped_column(String(10), default="zh-CN", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="CREATED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    episodes: Mapped[list["EpisodeM01"]] = relationship("EpisodeM01", back_populates="project")

    __table_args__ = (
        Index("idx_m01_project_status", "status"),
        Index("idx_m01_project_title", "title"),
    )


class EpisodeM01(Base):
    """剧集信息（M01 专用）"""
    __tablename__ = "episodes"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("m01_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    season_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    episode_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    project: Mapped["ProjectM01"] = relationship("ProjectM01", back_populates="episodes")
    media_assets: Mapped[list["MediaAsset"]] = relationship("MediaAsset", back_populates="episode")

    __table_args__ = (
        Index("idx_episode_project", "project_id"),
        Index("idx_episode_season_episode", "season_number", "episode_number"),
    )


class MediaAsset(Base):
    """媒体资产（M01 专用）"""
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    episode_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("episodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    container_format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    episode: Mapped[Optional["EpisodeM01"]] = relationship("EpisodeM01", back_populates="media_assets")
    streams: Mapped[list["MediaStream"]] = relationship("MediaStream", back_populates="media_asset", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_media_asset_episode", "episode_id"),
        Index("idx_media_asset_sha256", "sha256"),
    )


class MediaStream(Base):
    """媒体流信息（M01 专用）"""
    __tablename__ = "media_streams"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    media_id: Mapped[str] = mapped_column(String(50), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False)
    stream_type: Mapped[str] = mapped_column(String(20), nullable=False)  # video, audio, subtitle
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    codec_long: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    profile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    frame_rate: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bit_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    channels: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sample_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # 关系
    media_asset: Mapped["MediaAsset"] = relationship("MediaAsset", back_populates="streams")

    __table_args__ = (
        Index("idx_media_stream_media", "media_id"),
        Index("idx_media_stream_type", "stream_type"),
    )


class SubtitleAsset(Base):
    """字幕资产（M03 专用）"""
    __tablename__ = "subtitle_assets"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    episode_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    encoding: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_subtitle_asset_episode", "episode_id"),
        Index("idx_subtitle_asset_language", "language"),
    )


class JobEvent(Base):
    """作业事件（通用）"""
    __tablename__ = "job_events"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(50), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # INFO, WARNING, ERROR
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_job_event_job", "job_id"),
        Index("idx_job_event_timestamp", "timestamp"),
    )


# 为测试兼容性创建别名
Episode = EpisodeM01
Project = ProjectM01  # 默认使用 M01（用于 workers）

# Web UI 使用 ProjectRecord
WebProject = ProjectRecord
