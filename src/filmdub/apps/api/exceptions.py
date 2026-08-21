"""
统一响应格式和错误代码
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException
from fastapi.responses import JSONResponse
import time
import uuid


class ErrorResponse(Exception):
    """自定义错误响应"""
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class ErrorCode:
    """错误代码定义"""
    # 通用错误
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFLICT = "CONFLICT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    # 项目错误
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    PROJECT_ALREADY_EXISTS = "PROJECT_ALREADY_EXISTS"
    PROJECT_CANNOT_DELETE = "PROJECT_CANNOT_DELETE"

    # 作业错误
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_CANNOT_CANCEL = "JOB_CANNOT_CANCEL"
    JOB_ALREADY_COMPLETED = "JOB_ALREADY_COMPLETED"

    # Artifact 错误
    ARTIFACT_NOT_FOUND = "ARTIFACT_NOT_FOUND"
    ARTIFACT_UPLOAD_FAILED = "ARTIFACT_UPLOAD_FAILED"
    ARTIFACT_DOWNLOAD_FAILED = "ARTIFACT_DOWNLOAD_FAILED"

    # Worker 错误
    WORKER_NOT_FOUND = "WORKER_NOT_FOUND"
    WORKER_OFFLINE = "WORKER_OFFLINE"
    WORKER_BUSY = "WORKER_BUSY"


def success_response(
    data: Any = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    成功响应格式

    Args:
        data: 返回数据
        meta: 元数据

    Returns:
        统一响应格式
    """
    response = {
        "success": True,
        "data": data,
        "meta": {
            "timestamp": time.time(),
            "request_id": str(uuid.uuid4())
        }
    }

    if meta:
        response["meta"].update(meta)

    return response


def error_response(
    code: str,
    message: str,
    status_code: int = 400,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """
    错误响应格式

    Args:
        code: 错误代码
        message: 错误消息
        status_code: HTTP 状态码
        details: 额外细节

    Returns:
        JSON 响应
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details
            },
            "meta": {
                "timestamp": time.time(),
                "request_id": str(uuid.uuid4())
            }
        }
    )


def pagination_response(
    data: list,
    page: int,
    page_size: int,
    total: int,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    分页响应格式

    Args:
        data: 数据列表
        page: 当前页码
        page_size: 每页大小
        total: 总数
        meta: 元数据

    Returns:
        分页响应
    """
    total_pages = (total + page_size - 1) // page_size

    response = {
        "success": True,
        "data": data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        },
        "meta": {
            "timestamp": time.time(),
            "request_id": str(uuid.uuid4())
        }
    }

    if meta:
        response["meta"].update(meta)

    return response
