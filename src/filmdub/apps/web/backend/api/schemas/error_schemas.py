"""错误相关的 Pydantic schemas"""
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field


class ErrorType(str, Enum):
    """错误类型"""
    RECOVERABLE = "recoverable"  # 可恢复
    RETRYABLE = "retryable"  # 可重试
    MANUAL = "manual"  # 需人工干预
    FATAL = "fatal"  # 致命错误


class ErrorDetail(BaseModel):
    """错误详情"""
    error_code: str = Field(..., description="错误码")
    title: str = Field(..., description="错误标题")
    message: str = Field(..., description="错误消息")
    suggestion: Optional[str] = Field(None, description="操作建议")
    type: ErrorType = Field(..., description="错误类型")


class ErrorResponse(BaseModel):
    """标准错误响应"""
    success: bool = Field(False, description="是否成功")
    error: ErrorDetail = Field(..., description="错误详情")


class ErrorLogCreate(BaseModel):
    """创建错误日志"""
    job_id: Optional[str] = Field(None, description="关联的任务 ID")
    error_code: str = Field(..., description="错误码")
    title: str = Field(..., description="错误标题")
    message: str = Field(..., description="错误消息")
    suggestion: Optional[str] = Field(None, description="操作建议")
    error_type: ErrorType = Field(..., description="错误类型")
    stack_trace: Optional[str] = Field(None, description="堆栈跟踪")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class ErrorLogResponse(BaseModel):
    """错误日志响应"""
    id: str = Field(..., description="日志 ID")
    job_id: Optional[str] = Field(None, description="关联的任务 ID")
    error_code: str = Field(..., description="错误码")
    title: str = Field(..., description="错误标题")
    message: str = Field(..., description="错误消息")
    suggestion: Optional[str] = Field(None, description="操作建议")
    error_type: ErrorType = Field(..., description="错误类型")
    stack_trace: Optional[str] = Field(None, description="堆栈跟踪")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class ErrorLogListResponse(BaseModel):
    """错误日志列表响应"""
    total: int = Field(..., description="总数")
    items: list[ErrorLogResponse] = Field(..., description="日志列表")


class JobErrorLogsResponse(BaseModel):
    """任务错误日志响应"""
    job_id: str = Field(..., description="任务 ID")
    total_errors: int = Field(..., description="错误总数")
    logs: list[ErrorLogResponse] = Field(..., description="错误日志列表")
