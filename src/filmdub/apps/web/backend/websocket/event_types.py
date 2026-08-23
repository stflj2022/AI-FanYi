"""WebSocket 事件类型定义

定义所有 WebSocket 事件的格式和结构
"""
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class WebSocketEventType(str, Enum):
    """WebSocket 事件类型"""
    # 系统事件
    PING = "ping"
    PONG = "pong"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

    # 订阅事件
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"

    # 任务事件
    JOB_CREATED = "job.created"
    JOB_UPDATED = "job.updated"
    JOB_PROGRESS = "job.progress"
    JOB_STAGE = "job.stage"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_CANCELLED = "job.cancelled"
    JOB_RETRYING = "job.retrying"

    # Artifact 事件
    ARTIFACT_CREATED = "artifact.created"
    ARTIFACT_UPDATED = "artifact.updated"

    # 项目事件
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"


class BaseWebSocketEvent(BaseModel):
    """WebSocket 事件基类"""
    event_type: WebSocketEventType = Field(..., description="事件类型")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="事件时间戳")
    data: Dict[str, Any] = Field(default_factory=dict, description="事件数据")


class JobProgressEvent(BaseModel):
    """任务进度事件数据"""
    job_id: UUID = Field(..., description="任务 ID")
    progress: int = Field(..., ge=0, le=100, description="进度百分比")
    stage: Optional[str] = Field(None, description="当前阶段")
    message: Optional[str] = Field(None, description="进度消息")


class JobStageEvent(BaseModel):
    """任务阶段变化事件数据"""
    job_id: UUID = Field(..., description="任务 ID")
    stage: str = Field(..., description="新阶段")
    previous_stage: Optional[str] = Field(None, description="上一阶段")
    message: Optional[str] = Field(None, description="阶段变化消息")


class JobCompletedEvent(BaseModel):
    """任务完成事件数据"""
    job_id: UUID = Field(..., description="任务 ID")
    status: str = Field(..., description="最终状态")
    duration: Optional[float] = Field(None, description="执行时长（秒）")
    output_artifacts: Optional[list[str]] = Field(default_factory=list, description="输出 artifacts")


class JobFailedEvent(BaseModel):
    """任务失败事件数据"""
    job_id: UUID = Field(..., description="任务 ID")
    error_message: str = Field(..., description="错误消息")
    error_stack: Optional[str] = Field(None, description="错误堆栈")
    stage: Optional[str] = Field(None, description="失败时的阶段")


class JobRetryEvent(BaseModel):
    """任务重试事件数据"""
    job_id: UUID = Field(..., description="任务 ID")
    retry_count: int = Field(..., description="重试次数")
    max_retries: int = Field(..., description="最大重试次数")
    reason: Optional[str] = Field(None, description="重试原因")


class SubscribeRequest(BaseModel):
    """订阅请求"""
    action: str = Field(..., description="操作类型: subscribe/unsubscribe")
    job_id: UUID = Field(..., description="任务 ID")


class WebSocketError(BaseModel):
    """WebSocket 错误信息"""
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")


# 事件构建辅助函数
def build_event(
    event_type: WebSocketEventType,
    data: Dict[str, Any],
    job_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """构建 WebSocket 事件"""
    event = {
        "event_type": event_type.value,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
    }

    if job_id:
        event["job_id"] = str(job_id)

    return event


def build_progress_event(
    job_id: UUID,
    progress: int,
    stage: Optional[str] = None,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """构建任务进度事件"""
    return build_event(
        event_type=WebSocketEventType.JOB_PROGRESS,
        data={
            "job_id": str(job_id),
            "progress": progress,
            "stage": stage,
            "message": message,
        },
        job_id=job_id,
    )


def build_stage_event(
    job_id: UUID,
    stage: str,
    previous_stage: Optional[str] = None,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """构建任务阶段事件"""
    return build_event(
        event_type=WebSocketEventType.JOB_STAGE,
        data={
            "job_id": str(job_id),
            "stage": stage,
            "previous_stage": previous_stage,
            "message": message,
        },
        job_id=job_id,
    )


def build_completed_event(
    job_id: UUID,
    status: str,
    duration: Optional[float] = None,
    output_artifacts: Optional[list[str]] = None
) -> Dict[str, Any]:
    """构建任务完成事件"""
    return build_event(
        event_type=WebSocketEventType.JOB_COMPLETED,
        data={
            "job_id": str(job_id),
            "status": status,
            "duration": duration,
            "output_artifacts": output_artifacts or [],
        },
        job_id=job_id,
    )


def build_failed_event(
    job_id: UUID,
    error_message: str,
    error_stack: Optional[str] = None,
    stage: Optional[str] = None
) -> Dict[str, Any]:
    """构建任务失败事件"""
    return build_event(
        event_type=WebSocketEventType.JOB_FAILED,
        data={
            "job_id": str(job_id),
            "error_message": error_message,
            "error_stack": error_stack,
            "stage": stage,
        },
        job_id=job_id,
    )


def build_error_event(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """构建错误事件"""
    return build_event(
        event_type=WebSocketEventType.ERROR,
        data={
            "code": code,
            "message": message,
            "details": details,
        },
    )
