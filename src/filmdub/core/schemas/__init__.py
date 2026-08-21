"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ==================== Project Schemas ====================


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    title: str = Field(..., min_length=1, max_length=500, description="Project title")
    original_title: Optional[str] = Field(None, max_length=500, description="Original title in source language")
    target_language: str = Field(..., pattern=r"^[a-z]{2}-[A-Z]{2}$", description="Target language code (e.g., zh-CN)")


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    original_title: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, pattern=r"^(CREATED|INTAKE|READY_FOR_RESEARCH|PROCESSING|COMPLETED|FAILED|ARCHIVED)$")


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: str
    title: str
    original_title: Optional[str] = None
    target_language: str
    status: str
    created_at: datetime
    updated_at: datetime
    episode_count: int = 0

    class Config:
        from_attributes = True


# ==================== Episode Schemas ====================


class EpisodeCreate(BaseModel):
    """Schema for creating a new episode."""

    project_id: str
    season_number: Optional[int] = Field(None, ge=0, description="Season number")
    episode_number: Optional[int] = Field(None, ge=0, description="Episode number")
    title: Optional[str] = Field(None, max_length=500, description="Episode title")
    original_title: Optional[str] = Field(None, max_length=500, description="Original title")


class EpisodeResponse(BaseModel):
    """Schema for episode response."""

    id: str
    project_id: str
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    title: Optional[str] = None
    original_title: Optional[str] = None
    duration_seconds: Optional[float] = None
    status: str
    created_at: datetime
    updated_at: datetime
    media_count: int = 0

    class Config:
        from_attributes = True


# ==================== Media Schemas ====================


class MediaStreamResponse(BaseModel):
    """Schema for media stream response."""

    id: int
    stream_index: int
    stream_type: str  # video, audio, subtitle
    codec: Optional[str] = None
    language: Optional[str] = None
    title: Optional[str] = None
    is_default: bool
    is_forced: bool

    # Video-specific
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None

    # Audio-specific
    channels: Optional[int] = None
    channel_layout: Optional[str] = None
    sample_rate: Optional[int] = None
    bitrate: Optional[int] = None

    # Subtitle-specific
    subtitle_codec: Optional[str] = None

    class Config:
        from_attributes = True


class MediaResponse(BaseModel):
    """Schema for media asset response."""

    id: str
    episode_id: str
    original_filename: str
    file_size: int
    sha256: str
    duration_seconds: Optional[float] = None
    container_format: Optional[str] = None
    status: str
    created_at: datetime
    streams: list[MediaStreamResponse] = []

    class Config:
        from_attributes = True


class MediaOverview(BaseModel):
    """Schema for media overview."""

    video: Optional[MediaStreamResponse] = None
    audio: list[MediaStreamResponse] = []
    subtitles: list[MediaStreamResponse] = []
    chapters: int = 0


# ==================== Job Schemas ====================


class JobCreate(BaseModel):
    """Schema for creating a new job."""

    project_id: str
    episode_id: Optional[str] = None
    module: str = Field(..., description="Module name (e.g., media_intake, research, etc.)")
    input_manifest: Optional[str] = None


class JobResponse(BaseModel):
    """Schema for job response."""

    id: str
    project_id: str
    episode_id: Optional[str] = None
    module: str
    status: str  # PENDING, RUNNING, SUCCESS, FAILED, CANCELLED, SKIPPED
    attempt: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JobEventResponse(BaseModel):
    """Schema for job event response."""

    id: int
    job_id: str
    timestamp: datetime
    level: str  # DEBUG, INFO, WARNING, ERROR
    event_type: str
    message: Optional[str] = None
    payload: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== Manifest Schemas ====================


class MediaManifest(BaseModel):
    """Schema for media manifest."""

    schema_version: str = "1.0"
    media_id: str
    filename: str
    sha256: str
    container: dict
    video: dict
    audio: list[dict]
    subtitles: list[dict]
    chapters: list[dict]


class ProjectManifest(BaseModel):
    """Schema for project manifest."""

    schema_version: str = "1.0"
    project: dict
    episodes: list[dict]


# ==================== Filename Parse Result ====================


class FilenameParseResult(BaseModel):
    """Schema for parsed filename information."""

    title_candidate: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    quality: Optional[str] = None
    source: Optional[str] = None
    codec: Optional[str] = None
    release_group: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
