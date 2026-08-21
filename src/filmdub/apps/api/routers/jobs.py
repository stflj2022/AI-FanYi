"""
作业管理 API 路由
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.orchestrator.database import get_db
from filmdub.orchestrator.models import Job, JobStatus, Project, Worker, WorkerStatus
from filmdub.orchestrator.job_logs import job_log_store
from filmdub.apps.api.schemas import JobCreate, JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/projects/{project_id}", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    project_id: UUID,
    job_data: JobCreate,
    db: AsyncSession = Depends(get_db)
) -> JobResponse:
    """为项目创建新作业

    Args:
        project_id: 项目 ID
        job_data: 作业创建数据
        db: 数据库会话

    Returns:
        JobResponse: 创建的作业
    """
    # 检查项目是否存在
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # 检查依赖作业是否存在
    if job_data.depends_on:
        for dep_id in job_data.depends_on:
            dep_result = await db.execute(
                select(Job).where(Job.id == dep_id)
            )
            dep_job = dep_result.scalar_one_or_none()
            if not dep_job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Dependency job {dep_id} not found"
                )

    # 创建作业
    job = Job(
        project_id=project_id,
        name=job_data.name,
        status=JobStatus.PENDING,
        module_id=job_data.module_id,
        depends_on=job_data.depends_on or [],
        config=job_data.config,
    )

    db.add(job)
    await db.flush()
    await db.refresh(job)

    job_log_store.append(str(job.id), "created", f"Job '{job.name}' 创建，模块 {job.module_id}")

    return JobResponse.model_validate(job)


@router.get("/projects/{project_id}", response_model=List[JobResponse])
async def list_project_jobs(
    project_id: UUID,
    status_filter: Optional[str] = Query(None, alias="status", description="按状态过滤"),
    module_filter: Optional[str] = Query(None, alias="module", description="按模块过滤"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
) -> List[JobResponse]:
    """获取项目的作业列表

    Args:
        project_id: 项目 ID
        status_filter: 状态过滤器
        module_filter: 模块过滤器
        limit: 返回数量限制
        offset: 偏移量
        db: 数据库会话

    Returns:
        List[JobResponse]: 作业列表
    """
    # 检查项目是否存在
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # 构建查询
    query = select(Job).where(Job.project_id == project_id)

    # 状态过滤
    if status_filter:
        try:
            status_enum = JobStatus(status_filter)
            query = query.where(Job.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )

    # 模块过滤
    if module_filter:
        query = query.where(Job.module_id == module_filter)

    # 排序和分页
    query = query.order_by(Job.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return [JobResponse.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> JobResponse:
    """获取作业详情

    Args:
        job_id: 作业 ID
        db: 数据库会话

    Returns:
        JobResponse: 作业详情
    """
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    return JobResponse.model_validate(job)


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> JobResponse:
    """取消作业

    Args:
        job_id: 作业 ID
        db: 数据库会话

    Returns:
        JobResponse: 取消后的作业
    """
    # 获取作业
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # 检查状态
    if job.status not in [JobStatus.PENDING, JobStatus.SCHEDULED, JobStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status {job.status}"
        )

    # 更新状态
    job.status = JobStatus.CANCELLED
    await db.flush()
    await db.refresh(job)

    # 通知 Worker 停止执行：释放被占用的 Worker，并向其广播取消指令
    released_worker = None
    if job.worker_id:
        worker_result = await db.execute(
            select(Worker).where(Worker.id == job.worker_id)
        )
        released_worker = worker_result.scalar_one_or_none()
        if released_worker:
            released_worker.current_job_id = None
            released_worker.status = WorkerStatus.IDLE

    job_log_store.append(
        str(job_id),
        "cancelled",
        f"Job 被取消" + (f"，Worker {released_worker.name} 已释放" if released_worker else ""),
    )

    # 通过 WebSocket 向 Worker 频道广播取消指令（尽力而为）
    try:
        from filmdub.apps.api.websocket.manager import ConnectionManager
        manager = ConnectionManager()
        await manager.broadcast(
            {
                "type": "job_command",
                "command": "cancel_job",
                "job_id": str(job_id),
                "project_id": str(job.project_id),
            },
            channel=f"worker:{job.worker_id}" if job.worker_id else None,
        )
    except Exception as e:
        import logging as _logging
        _logging.getLogger(__name__).warning("Failed to broadcast cancel command: %s", e)

    return JobResponse.model_validate(job)


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> JobResponse:
    """重试失败的作业

    Args:
        job_id: 作业 ID
        db: 数据库会话

    Returns:
        JobResponse: 重试后的作业
    """
    # 获取作业
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # 检查状态
    if job.status != JobStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only retry failed jobs, current status: {job.status}"
        )

    # 检查重试次数
    if job.retry_count >= job.max_retries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job has reached maximum retry count ({job.max_retries})"
        )

    # 更新状态：回到 PENDING，由调度器下一轮重新分发
    job.status = JobStatus.PENDING
    job.worker_id = None
    job.retry_count += 1
    job.error_message = None
    job.error_stack = None
    job.scheduled_at = None
    await db.flush()
    await db.refresh(job)

    job_log_store.append(
        str(job_id),
        "retried",
        f"Job 重试（第 {job.retry_count} 次），已回到待调度队列",
        {"retry_count": job.retry_count},
    )

    return JobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """删除作业

    Args:
        job_id: 作业 ID
        db: 数据库会话
    """
    # 获取作业
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
    )

    # 检查状态
    if job.status == JobStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete running job"
        )

    # 删除作业
    await db.execute(delete(Job).where(Job.id == job_id))
    await db.flush()


@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """获取作业日志

    Args:
        job_id: 作业 ID
        db: 数据库会话

    Returns:
        dict: 日志信息
    """
    # 获取作业
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # 从日志存储中读取实际日志
    log_entries = job_log_store.read(str(job_id))

    return {
        "job_id": str(job_id),
        "project_id": str(job.project_id),
        "status": job.status.value,
        "error_message": job.error_message,
        "error_stack": job.error_stack,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "logs": log_entries,
    }
