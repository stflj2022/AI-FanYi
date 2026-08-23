"""上传相关的 Pydantic schemas"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class UploadStatus(str, Enum):
    """上传状态"""
    PENDING = "pending"
    UPLOADING = "uploading"
    READY = "ready"
    FAILED = "failed"


class MediaType(str, Enum):
    """媒体类型"""
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"


class UploadResponse(BaseModel):
    """上传响应"""
    id: UUID
    status: UploadStatus
    filename: str
    file_size: int
    mime_type: str
    project_id: Optional[UUID] = None
    media_type: MediaType
    progress: float = 0.0
    created_at: datetime
    updated_at: datetime


class UploadProgressResponse(BaseModel):
    """上传进度响应"""
    id: UUID
    status: UploadStatus
    progress: float
    bytes_uploaded: int
    total_bytes: int
    speed_bytes_per_sec: Optional[float] = None
    estimated_seconds_remaining: Optional[float] = None


class MediaMetadataResponse(BaseModel):
    """媒体元数据响应"""
    id: UUID
    media_asset_id: str
    filename: str
    duration_seconds: Optional[float] = None
    format: Optional[str] = None
    streams: list[Dict[str, Any]] = Field(default_factory=list)
    video_streams: list[Dict[str, Any]] = Field(default_factory=list)
    audio_streams: list[Dict[str, Any]] = Field(default_factory=list)
    subtitle_streams: list[Dict[str, Any]] = Field(default_factory=list)


class UploadError(BaseModel):
    """上传错误"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    error: UploadError
