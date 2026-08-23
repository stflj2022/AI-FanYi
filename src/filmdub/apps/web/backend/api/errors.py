"""错误日志 API 端点"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from filmdub.core.orchestrator_db import get_db
from filmdub.apps.web.backend.models import User
from filmdub.apps.web.backend.api.dependencies import get_current_active_user
from filmdub.apps.web.backend.api.schemas.error_schemas import (
    ErrorLogResponse,
    ErrorLogListResponse,
    JobErrorLogsResponse,
)

router = APIRouter()


@router.get("/logs", response_model=ErrorLogListResponse)
async def list_error_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    job_id: Optional[str] = Query(None, description="任务 ID 筛选"),
    error_code: Optional[str] = Query(None, description="错误码筛选"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取错误日志列表"""
    from filmdub.core.models import ErrorLog

    # 构建查询
    query = select(ErrorLog)
    count_query = select(ErrorLog.id)

    # 筛选条件
    filters = []

    if job_id:
        try:
            job_uuid = uuid.UUID(job_id)
            filters.append(ErrorLog.job_id == job_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的任务 ID"
            )

    if error_code:
        filters.append(ErrorLog.error_code == error_code)

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    # 排序（最新的在前）
    query = query.order_by(desc(ErrorLog.created_at))

    # 获取总数
    total_result = await db.execute(select(count_query).subquery())
    total = len(total_result.all())

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)

    # 执行查询
    result = await db.execute(query)
    logs = result.scalars().all()

    return ErrorLogListResponse(
        total=total,
        items=[ErrorLogResponse.model_validate(log) for log in logs],
    )


@router.get("/jobs/{job_id}/logs", response_model=JobErrorLogsResponse)
async def get_job_error_logs(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定任务的错误日志"""
    from filmdub.core.models import ErrorLog, Job

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的任务 ID"
        )

    # 验证任务是否存在且用户有权限访问
    job_result = await db.execute(
        select(Job).filter(Job.id == job_uuid)
    )
    job = job_result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    # 获取错误日志
    logs_result = await db.execute(
        select(ErrorLog)
        .filter(ErrorLog.job_id == job_uuid)
        .order_by(desc(ErrorLog.created_at))
    )
    logs = logs_result.scalars().all()

    return JobErrorLogsResponse(
        job_id=job_id,
        total_errors=len(logs),
        logs=[ErrorLogResponse.model_validate(log) for log in logs],
    )


@router.get("/logs/{log_id}", response_model=ErrorLogResponse)
async def get_error_log(
    log_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取错误日志详情"""
    from filmdub.core.models import ErrorLog

    try:
        log_uuid = uuid.UUID(log_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的日志 ID"
        )

    result = await db.execute(
        select(ErrorLog).filter(ErrorLog.id == log_uuid)
    )
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="错误日志不存在"
        )

    return ErrorLogResponse.model_validate(log)
