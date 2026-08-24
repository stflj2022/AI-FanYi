"""任务 API 端点"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.core.orchestrator_db import get_db
from filmdub.core.models import ProjectRecord
from filmdub.apps.web.backend.services.job_service import JobService
from filmdub.apps.web.backend.models import User
from filmdub.apps.web.backend.api.dependencies import get_current_active_user
from filmdub.apps.web.backend.api.schemas.job_schemas import (
    JobCreate,
    JobUpdate,
    JobResponse,
    JobListResponse,
    JobActionResponse,
    JobActionRequest,
    JobStatus,
    JobQueryParams,
    JobStatsResponse,
    RecentJobsResponse,
)
from filmdub.apps.web.backend.websocket.events import (
    publish_job_created,
    publish_job_status_changed,
)

router = APIRouter()


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """创建任务"""
    job = await JobService.create_job(
        db=db,
        job_data=job_data,
        owner_id=current_user.id,
    )

    # 发布任务创建实时事件（Dashboard / 任务列表页刷新）
    await publish_job_created(
        job_id=job.id,
        job_name=job.name,
        project_id=job.project_id,
        user_id=current_user.id,
    )

    return JobResponse.model_validate(job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    project_id: Optional[str] = Query(None, description="项目 ID 筛选"),
    status: Optional[JobStatus] = Query(None, description="状态筛选"),
    module_id: Optional[str] = Query(None, description="模块 ID 筛选"),
    worker_id: Optional[str] = Query(None, description="Worker ID 筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取任务列表（支持分页、搜索和筛选）"""
    # 转换项目 ID 和 Worker ID
    project_uuid = uuid.UUID(project_id) if project_id else None
    worker_uuid = uuid.UUID(worker_id) if worker_id else None

    jobs, total = await JobService.list_jobs(
        db=db,
        owner_id=current_user.id,
        project_id=project_uuid,
        status_filter=status.value if status else None,
        module_id=module_id,
        worker_id=worker_uuid,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return JobListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[JobResponse.model_validate(j) for j in jobs],
    )


# Dashboard 相关端点（必须在 /{job_id} 之前定义）
@router.get("/stats", response_model=JobStatsResponse)
async def get_job_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取任务统计信息"""
    stats = await JobService.get_job_stats(
        db=db,
        owner_id=current_user.id,
    )
    return JobStatsResponse(**stats)


@router.get("/recent", response_model=RecentJobsResponse)
async def get_recent_jobs(
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取最近的任务列表"""
    jobs = await JobService.get_recent_jobs(
        db=db,
        owner_id=current_user.id,
        limit=limit,
    )
    return RecentJobsResponse(
        items=[JobResponse.model_validate(j) for j in jobs]
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取任务详情"""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的任务 ID"
        )

    job = await JobService.get_job_by_id(
        db=db,
        job_id=job_uuid,
        owner_id=current_user.id,
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权访问"
        )

    return JobResponse.model_validate(job)


async def _get_job_or_404(job_id: str, current_user: User, db: AsyncSession):
    """解析并获取任务，不存在则 404"""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的任务 ID")
    job = await JobService.get_job_by_id(db=db, job_id=job_uuid, owner_id=current_user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在或无权访问")
    return job


@router.get("/{job_id}/output/video")
async def get_job_output_video(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取任务最终配音视频（在线播放/下载）"""
    job = await _get_job_or_404(job_id, current_user, db)

    object_name = None
    for art in (job.output_artifacts or []):
        if art.startswith("final_video:"):
            object_name = art.split(":", 1)[1]
            break
    if not object_name:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务暂无成品视频")

    from minio import Minio
    import os, tempfile

    minio_client = Minio(
        os.environ.get("MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin123"),
        secure=False,
    )
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    try:
        minio_client.fget_object("filmdub-uploads", object_name, tmp.name)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"成品视频读取失败: {e}")

    from fastapi.responses import FileResponse
    from starlette.background import BackgroundTask

    def _cleanup(path: str):
        import os
        try:
            os.unlink(path)
        except OSError:
            pass

    return FileResponse(
        tmp.name,
        media_type="video/mp4",
        filename=f"{job.name}.mp4",
        background=BackgroundTask(_cleanup, tmp.name),
    )


@router.get("/{job_id}/output/qa-report")
async def get_job_qa_report(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取任务 QA 报告"""
    job = await _get_job_or_404(job_id, current_user, db)
    qa_score = (job.config or {}).get("qa_score") if job.config else None
    return {
        "job_id": str(job.id),
        "name": job.name,
        "status": job.status.value if hasattr(job.status, "value") else str(job.status),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "overall_score": qa_score,
        "issues": [],
        "details": {
            "status": job.status.value if hasattr(job.status, "value") else str(job.status),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "output_artifacts": job.output_artifacts or [],
        },
    }


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    job_data: JobUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """更新任务"""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的任务 ID"
        )

    job = await JobService.update_job(
        db=db,
        job_id=job_uuid,
        job_data=job_data,
        owner_id=current_user.id,
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权访问"
        )

    return JobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """删除任务"""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的任务 ID"
        )

    success = await JobService.delete_job(
        db=db,
        job_id=job_uuid,
        owner_id=current_user.id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权访问"
        )


@router.post("/{job_id}/pause", response_model=JobActionResponse)
async def pause_job(
    job_id: str,
    action_data: JobActionRequest = JobActionRequest(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """暂停任务"""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的任务 ID"
        )

    job = await JobService.pause_job(
        db=db,
        job_id=job_uuid,
        reason=action_data.reason,
        owner_id=current_user.id,
    )

    # 发布任务状态变更实时事件
    await publish_job_status_changed(
        job_id=job.id,
        new_status=job.status.value if hasattr(job.status, "value") else str(job.status),
        old_status=None,
        user_id=current_user.id,
    )

    return JobActionResponse(
        id=job.id,
        status=job.status,
        message="任务已暂停"
    )


@router.post("/{job_id}/resume", response_model=JobActionResponse)
async def resume_job(
    job_id: str,
    action_data: JobActionRequest = JobActionRequest(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """恢复任务"""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的任务 ID"
        )

    job = await JobService.resume_job(
        db=db,
        job_id=job_uuid,
        reason=action_data.reason,
        owner_id=current_user.id,
    )

    # 发布任务状态变更实时事件
    await publish_job_status_changed(
        job_id=job.id,
        new_status=job.status.value if hasattr(job.status, "value") else str(job.status),
        old_status=None,
        user_id=current_user.id,
    )

    return JobActionResponse(
        id=job.id,
        status=job.status,
        message="任务已恢复"
    )


@router.post("/{job_id}/cancel", response_model=JobActionResponse)
async def cancel_job(
    job_id: str,
    action_data: JobActionRequest = JobActionRequest(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """取消任务"""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的任务 ID"
        )

    job = await JobService.cancel_job(
        db=db,
        job_id=job_uuid,
        reason=action_data.reason,
        owner_id=current_user.id,
    )

    # 发布任务状态变更实时事件
    await publish_job_status_changed(
        job_id=job.id,
        new_status=job.status.value if hasattr(job.status, "value") else str(job.status),
        old_status=None,
        user_id=current_user.id,
    )

    return JobActionResponse(
        id=job.id,
        status=job.status,
        message="任务已取消"
    )


@router.post("/{job_id}/retry", response_model=JobActionResponse)
async def retry_job(
    job_id: str,
    action_data: JobActionRequest = JobActionRequest(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """重试任务"""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的任务 ID"
        )

    job = await JobService.retry_job(
        db=db,
        job_id=job_uuid,
        reason=action_data.reason,
        owner_id=current_user.id,
    )

    # 发布任务状态变更实时事件
    await publish_job_status_changed(
        job_id=job.id,
        new_status=job.status.value if hasattr(job.status, "value") else str(job.status),
        old_status=None,
        user_id=current_user.id,
    )

    return JobActionResponse(
        id=job.id,
        status=job.status,
        message="任务已重新调度"
    )


# 内部端点（供 Worker 或 Orchestrator 调用）
@router.post("/{job_id}/sync", response_model=JobResponse)
async def sync_job_status(
    job_id: str,
    status: str = Query(..., description="任务状态"),
    error_message: Optional[str] = Query(None, description="错误消息"),
    output_artifacts: Optional[str] = Query(None, description="输出 artifacts (JSON 数组)"),
    db: AsyncSession = Depends(get_db),
):
    """
    同步任务状态（内部端点）

    供 Worker 或 Orchestrator 调用以更新任务状态。
    此端点不需要认证，建议在生产环境中通过 API Key 或内部网络保护。
    """
    import json

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的任务 ID"
        )

    # 解析 output_artifacts
    artifacts = None
    if output_artifacts:
        try:
            artifacts = json.loads(output_artifacts)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="output_artifacts 格式错误"
            )

    job = await JobService.sync_job_status(
        db=db,
        job_id=job_uuid,
        status=status,
        error_message=error_message,
        output_artifacts=artifacts,
    )

    # 发布任务状态变更实时事件（Worker/Orchestrator 驱动的状态流转，推送给任务属主）
    owner_id = None
    if job.project_id:
        proj_result = await db.execute(
            select(ProjectRecord).filter(ProjectRecord.id == job.project_id)
        )
        proj = proj_result.scalar_one_or_none()
        if proj:
            owner_id = proj.created_by

    await publish_job_status_changed(
        job_id=job.id,
        new_status=job.status.value if hasattr(job.status, "value") else str(job.status),
        old_status=None,
        user_id=owner_id,
    )

    return JobResponse.model_validate(job)
