"""任务相关的 Pydantic schemas"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobCreate(BaseModel):
    """创建任务请求"""
    project_id: UUID = Field(..., description="项目 ID")
    name: str = Field(..., min_length=1, max_length=255, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    workflow_id: Optional[UUID] = Field(None, description="工作流 ID")
    module_id: Optional[str] = Field(None, description="模块 ID")
    input_artifacts: Optional[List[str]] = Field(default_factory=list, description="输入 artifacts ID 列表")
    depends_on: Optional[List[UUID]] = Field(default_factory=list, description="依赖的任务 ID 列表")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="任务配置")


class JobUpdate(BaseModel):
    """更新任务请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class JobResponse(BaseModel):
    """任务响应"""
    id: UUID
    project_id: UUID
    name: str
    status: JobStatus
    description: Optional[str] = None

    # 执行信息
    module_id: Optional[str] = None
    worker_id: Optional[UUID] = None
    retry_count: int = 0
    max_retries: int = 3

    # 依赖
    depends_on: Optional[List[UUID]] = None

    # 时间
    created_at: datetime
    updated_at: datetime
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 输入输出
    input_artifacts: Optional[List[str]] = None
    output_artifacts: Optional[List[str]] = None

    # 错误信息
    error_message: Optional[str] = None
    error_stack: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    """任务列表响应"""
    total: int
    page: int
    page_size: int
    items: List[JobResponse]


class JobActionResponse(BaseModel):
    """任务操作响应"""
    id: UUID
    status: JobStatus
    message: str


class JobActionRequest(BaseModel):
    """任务操作请求"""
    reason: Optional[str] = Field(None, description="操作原因")


class JobQueryParams(BaseModel):
    """任务查询参数"""
    project_id: Optional[UUID] = None
    status: Optional[JobStatus] = None
    module_id: Optional[str] = None
    worker_id: Optional[UUID] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class JobStatsResponse(BaseModel):
    """任务统计响应"""
    total: int = Field(..., description="总任务数")
    pending: int = Field(..., description="等待中的任务")
    scheduled: int = Field(..., description="已调度的任务")
    running: int = Field(..., description="运行中的任务")
    waiting: int = Field(..., description="等待中的任务（已暂停）")
    completed: int = Field(..., description="已完成的任务")
    failed: int = Field(..., description="失败的任务")
    cancelled: int = Field(..., description="已取消的任务")
    retrying: int = Field(..., description="重试中的任务")
    active: int = Field(..., description="活跃任务数（运行中+重试中）")
    finished: int = Field(..., description="已结束任务数（完成+失败+取消）")


class RecentJobsResponse(BaseModel):
    """最近任务响应"""
    items: List[JobResponse] = Field(..., description="最近任务列表")
