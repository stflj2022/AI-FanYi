"""
项目管理 API 路由
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.orchestrator.database import get_db
from filmdub.orchestrator.models import (
    Project,
    ProjectStatus,
    Job,
    JobStatus,
    Artifact,
)
from filmdub.orchestrator.job_logs import job_log_store
from filmdub.apps.api.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectStatistics,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db)
) -> ProjectResponse:
    """创建新项目

    Args:
        project_data: 项目创建数据
        db: 数据库会话

    Returns:
        ProjectResponse: 创建的项目
    """
    # 检查 TMDB ID 是否已存在
    if project_data.tmdb_id:
        result = await db.execute(
            select(Project).where(Project.tmdb_id == project_data.tmdb_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project with TMDB ID {project_data.tmdb_id} already exists"
            )

    # 创建项目
    project = Project(
        name=project_data.name,
        description=project_data.description,
        status=ProjectStatus.PENDING,
        media_type=project_data.media_type,
        title=project_data.title,
        title_en=project_data.title_en,
        season=project_data.season,
        episode=project_data.episode,
        year=project_data.year,
        original_language=project_data.original_language,
        target_language=project_data.target_language,
        tmdb_id=project_data.tmdb_id,
        imdb_id=project_data.imdb_id,
        workflow_id=project_data.workflow_id,
        config=project_data.config,
    )

    db.add(project)
    await db.flush()
    await db.refresh(project)

    return ProjectResponse.model_validate(project)


@router.get("", response_model=List[ProjectListResponse])
async def list_projects(
    status_filter: Optional[str] = Query(None, alias="status", description="按状态过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db)
) -> List[ProjectListResponse]:
    """获取项目列表

    Args:
        status_filter: 状态过滤器
        limit: 返回数量限制
        offset: 偏移量
        db: 数据库会话

    Returns:
        List[ProjectListResponse]: 项目列表
    """
    query = select(Project)

    # 状态过滤
    if status_filter:
        try:
            status_enum = ProjectStatus(status_filter)
            query = query.where(Project.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )

    # 排序和分页
    query = query.order_by(Project.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    projects = result.scalars().all()

    return [
        ProjectListResponse(
            id=p.id,
            name=p.name,
            status=p.status.value,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ProjectResponse:
    """获取项目详情

    Args:
        project_id: 项目 ID
        db: 数据库会话

    Returns:
        ProjectResponse: 项目详情
    """
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    db: AsyncSession = Depends(get_db)
) -> ProjectResponse:
    """更新项目

    Args:
        project_id: 项目 ID
        project_update: 更新数据
        db: 数据库会话

    Returns:
        ProjectResponse: 更新后的项目
    """
    # 获取项目
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # 更新字段
    update_data = project_update.model_dump(exclude_unset=True)

    # 状态验证
    if "status" in update_data:
        try:
            ProjectStatus(update_data["status"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {update_data['status']}"
            )

    for field, value in update_data.items():
        setattr(project, field, value)

    await db.flush()
    await db.refresh(project)

    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """删除项目

    Args:
        project_id: 项目 ID
        db: 数据库会话
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

    # 检查是否有运行中的作业
    job_result = await db.execute(
        select(func.count()).select_from(Job).where(
            Job.project_id == project_id,
            Job.status.in_(["running", "scheduled"])
        )
    )
    active_jobs = job_result.scalar() or 0

    if active_jobs > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete project with {active_jobs} active job(s)"
        )

    # 删除项目（级联删除会处理关联的作业和 artifacts）
    await db.execute(delete(Project).where(Project.id == project_id))
    await db.flush()


@router.get("/{project_id}/statistics", response_model=ProjectStatistics)
async def get_project_statistics(
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ProjectStatistics:
    """获取项目统计信息

    Args:
        project_id: 项目 ID
        db: 数据库会话

    Returns:
        ProjectStatistics: 统计信息
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

    # 统计作业
    job_stats = await db.execute(
        select(Job.status, func.count(Job.id))
        .where(Job.project_id == project_id)
        .group_by(Job.status)
    )

    stats = {status: 0 for status in ["pending", "running", "completed", "failed", "cancelled"]}
    for job_status, count in job_stats.all():
        stats[job_status] = count

    return ProjectStatistics(
        total_jobs=sum(stats.values()),
        completed_jobs=stats.get("completed", 0),
        failed_jobs=stats.get("failed", 0),
        running_jobs=stats.get("running", 0),
        pending_jobs=stats.get("pending", 0),
    )


@router.post("/{project_id}/start", status_code=status.HTTP_202_ACCEPTED)
async def start_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """启动项目处理

    Args:
        project_id: 项目 ID
        db: 数据库会话

    Returns:
        dict: 启动结果
    """
    # 获取项目
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # 检查状态
    if project.status == ProjectStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is already processing"
        )

    # 更新状态
    project.status = ProjectStatus.PROCESSING
    project.started_at = datetime.utcnow()
    await db.flush()

    # 触发调度器：解析依赖、匹配 Worker 并分发就绪作业
    dispatched = 0
    try:
        from filmdub.orchestrator.scheduler import (
            DependencyResolver,
            ResourceMatcher,
            DispatchEngine,
        )
        from filmdub.orchestrator.jwt_handler import JWTHandler

        resolver = DependencyResolver(db)
        matcher = ResourceMatcher(db)
        engine = DispatchEngine(db, JWTHandler())

        ready_jobs = await resolver.get_ready_jobs(project_id)
        for job in ready_jobs:
            require_gpu = job.module_id == "M09"
            worker = await matcher.find_best_worker(job, require_gpu=require_gpu)
            if worker:
                await engine.dispatch_job(job, worker)
                dispatched += 1

        job_log_store.append(
            str(project_id),
            "project_started",
            f"项目启动，分发 {dispatched} 个就绪作业",
            {"dispatched": dispatched},
        )
    except Exception as e:
        import logging as _logging
        _logging.getLogger(__name__).warning("Scheduler dispatch failed on project start: %s", e)

    return {
        "message": "Project started",
        "project_id": str(project_id),
        "status": project.status.value,
        "dispatched_jobs": dispatched,
    }


@router.post("/{project_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """取消项目

    Args:
        project_id: 项目 ID
        db: 数据库会话

    Returns:
        dict: 取消结果
    """
    # 获取项目
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # 检查状态
    if project.status not in [ProjectStatus.PROCESSING, ProjectStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel project with status {project.status}"
        )

    # 更新状态
    project.status = ProjectStatus.CANCELLED
    await db.flush()

    # 取消运行中的作业：将待处理/已调度/运行中/重试中的作业标记为取消
    active_statuses = [
        JobStatus.PENDING,
        JobStatus.SCHEDULED,
        JobStatus.RUNNING,
        JobStatus.RETRYING,
    ]
    job_result = await db.execute(
        select(Job).where(
            Job.project_id == project_id,
            Job.status.in_(active_statuses),
        )
    )
    active_jobs = job_result.scalars().all()

    cancelled = 0
    for job in active_jobs:
        job.status = JobStatus.CANCELLED
        cancelled += 1
        job_log_store.append(
            str(job.id),
            "cancelled",
            f"项目取消，作业 '{job.name}' 被终止",
        )

    job_log_store.append(
        str(project_id),
        "project_cancelled",
        f"项目取消，共终止 {cancelled} 个作业",
        {"cancelled_jobs": cancelled},
    )

    return {
        "message": "Project cancelled",
        "project_id": str(project_id),
        "status": project.status.value,
        "cancelled_jobs": cancelled,
    }
