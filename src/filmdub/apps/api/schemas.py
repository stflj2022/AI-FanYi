"""
Pydantic 模型用于请求/响应验证
"""
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ==================== 项目相关 ====================

class ProjectCreate(BaseModel):
    """创建项目请求"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    media_type: Optional[str] = None
    title: Optional[str] = None
    title_en: Optional[str] = None
    season: Optional[int] = Field(None, ge=1)
    episode: Optional[int] = Field(None, ge=1)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    original_language: str = "en"
    target_language: str = "zh-CN"
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    workflow_id: Optional[UUID] = None
    config: Optional[dict] = None


class ProjectUpdate(BaseModel):
    """更新项目请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    config: Optional[dict] = None


class ProjectResponse(BaseModel):
    """项目响应"""
    id: UUID
    name: str
    description: Optional[str]
    status: str
    media_type: Optional[str]
    title: Optional[str]
    title_en: Optional[str]
    season: Optional[int]
    episode: Optional[int]
    year: Optional[int]
    original_language: str
    target_language: str
    tmdb_id: Optional[int]
    imdb_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_by: Optional[UUID]
    assigned_to: Optional[UUID]
    workflow_id: Optional[UUID]
    config: Optional[dict]


class ProjectListResponse(BaseModel):
    """项目列表响应"""
    id: UUID
    name: str
    status: str
    created_at: datetime
    updated_at: datetime
    # 可以添加统计信息


class ProjectStatistics(BaseModel):
    """项目统计"""
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    running_jobs: int
    pending_jobs: int


# ==================== 作业相关 ====================

class JobCreate(BaseModel):
    """创建作业请求"""
    name: str = Field(..., min_length=1, max_length=255)
    module_id: str = Field(..., min_length=1, max_length=20)
    depends_on: Optional[List[UUID]] = None
    config: Optional[dict] = None


class JobResponse(BaseModel):
    """作业响应"""
    id: UUID
    project_id: UUID
    name: str
    status: str
    module_id: Optional[str]
    worker_id: Optional[UUID]
    retry_count: int
    max_retries: int
    depends_on: Optional[List[UUID]]
    created_at: datetime
    updated_at: datetime
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    input_artifacts: Optional[List[UUID]]
    output_artifacts: Optional[List[UUID]]
    error_message: Optional[str]
    error_stack: Optional[str]
    progress: float = 0  # 进度百分比 0-100


class JobListResponse(BaseModel):
    """作业列表响应"""
    id: UUID
    name: str
    status: str
    module_id: Optional[str]
    progress: float
    created_at: datetime
    updated_at: datetime


# ==================== Artifact 相关 ====================

class ArtifactCreate(BaseModel):
    """创建 Artifact 请求"""
    name: str = Field(..., min_length=1, max_length=255)
    type: str
    project_id: UUID
    job_id: Optional[UUID] = None
    module_id: Optional[str] = None
    mime_type: Optional[str] = None


class ArtifactResponse(BaseModel):
    """Artifact 响应"""
    id: UUID
    name: str
    type: str
    status: str
    project_id: UUID
    job_id: Optional[UUID]
    module_id: Optional[str]
    size_bytes: Optional[int]
    mime_type: Optional[str]
    created_at: datetime
    updated_at: datetime
    accessed_at: Optional[datetime]
    version: int


class ArtifactListResponse(BaseModel):
    """Artifact 列表响应"""
    id: UUID
    name: str
    type: str
    status: str
    size_bytes: Optional[int]
    created_at: datetime


# ==================== Worker 相关 ====================

class WorkerResponse(BaseModel):
    """Worker 响应"""
    id: UUID
    name: str
    status: str
    type: str
    cpu_cores: Optional[int]
    memory_gb: Optional[int]
    gpu_count: int
    gpu_memory_gb: int
    jobs_completed: int
    jobs_failed: int
    last_heartbeat: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# ==================== 统计相关 ====================

class SystemOverviewStatistics(BaseModel):
    """系统概览统计"""
    projects: ProjectStatistics
    jobs: Dict[str, int]
    workers: Dict[str, int]
    artifacts: Dict[str, int]
