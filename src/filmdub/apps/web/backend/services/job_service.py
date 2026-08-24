"""任务服务"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, asc, func
from sqlalchemy.orm import selectinload

from filmdub.core.models import Job, Workflow, Worker, ProjectRecord
from filmdub.core.orchestrator_db import get_db_context
from fastapi import HTTPException, status


class JobService:
    """任务服务"""

    @staticmethod
    async def create_job(
        db: AsyncSession,
        job_data: "JobCreate",
        owner_id: Optional[uuid.UUID] = None,
    ) -> Job:
        """创建任务"""
        # 验证项目是否存在
        project_result = await db.execute(
            select(ProjectRecord).filter(ProjectRecord.id == job_data.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在"
            )

        # 如果指定了 workflow_id，验证工作流是否存在
        if job_data.workflow_id:
            workflow_result = await db.execute(
                select(Workflow).filter(Workflow.id == job_data.workflow_id)
            )
            workflow = workflow_result.scalar_one_or_none()
            if not workflow:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="工作流不存在"
                )

        # 验证依赖的任务是否存在
        if job_data.depends_on:
            depends_result = await db.execute(
                select(Job.id).filter(Job.id.in_(job_data.depends_on))
            )
            existing_ids = {row[0] for row in depends_result}
            missing_ids = set(job_data.depends_on) - existing_ids
            if missing_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"依赖的任务不存在: {missing_ids}"
                )

        # 创建任务
        job = Job(
            project_id=job_data.project_id,
            name=job_data.name,
            description=job_data.description,
            workflow_id=job_data.workflow_id,
            module_id=job_data.module_id,
            input_artifacts=job_data.input_artifacts,
            depends_on=[str(d) for d in job_data.depends_on],
            status="pending",  # 使用字符串值
            config=job_data.config or {},
        )
        db.add(job)
        await db.flush()

        # 如果指定了工作流，自动调度任务
        if job_data.workflow_id:
            await JobService._schedule_job(db, job)

        await db.commit()
        await db.refresh(job)

        return job

    @staticmethod
    async def _schedule_job(db: AsyncSession, job: Job):
        """调度任务（内部方法）"""
        job.status = "scheduled"  # 使用字符串值
        job.scheduled_at = datetime.utcnow()
        # TODO: 调用 Layer 0 Orchestrator 实际调度任务

    @staticmethod
    async def get_job_by_id(
        db: AsyncSession,
        job_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
    ) -> Optional[Job]:
        """根据 ID 获取任务"""
        query = select(Job).filter(Job.id == job_id)

        # 如果指定了 owner_id，验证项目所有权
        if owner_id:
            query = query.join(ProjectRecord).filter(
                ProjectRecord.created_by == owner_id
            )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_jobs(
        db: AsyncSession,
        owner_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        module_id: Optional[str] = None,
        worker_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Job], int]:
        """获取任务列表"""
        # 构建基础查询
        query = select(Job)
        count_query = select(func.count()).select_from(Job)

        # 关联项目以验证所有权
        if owner_id:
            query = query.join(ProjectRecord).filter(ProjectRecord.created_by == owner_id)
            count_query = count_query.join(ProjectRecord).filter(ProjectRecord.created_by == owner_id)

        # 应用筛选条件
        filters = []

        if project_id:
            filters.append(Job.project_id == project_id)

        if status_filter:
            filters.append(Job.status == status_filter)

        if module_id:
            filters.append(Job.module_id == module_id)

        if worker_id:
            filters.append(Job.worker_id == worker_id)

        if search:
            search_pattern = f"%{search}%"
            filters.append(Job.name.ilike(search_pattern))

        if filters:
            query = query.filter(and_(*filters))
            count_query = count_query.filter(and_(*filters))

        # 排序
        sort_column = getattr(Job, sort_by, Job.created_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # 获取总数
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # 分页
        query = query.offset((page - 1) * page_size).limit(page_size)

        # 执行查询
        result = await db.execute(query)
        jobs = result.scalars().all()

        return list(jobs), total

    @staticmethod
    async def update_job(
        db: AsyncSession,
        job_id: uuid.UUID,
        job_data: "JobUpdate",
        owner_id: Optional[uuid.UUID] = None,
    ) -> Optional[Job]:
        """更新任务"""
        job = await JobService.get_job_by_id(db, job_id, owner_id)
        if not job:
            return None

        # 只允许更新特定字段
        if job_data.name is not None:
            job.name = job_data.name
        if job_data.description is not None:
            job.description = job_data.description
        if job_data.config is not None:
            job.config = job_data.config

        job.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(job)

        return job

    @staticmethod
    async def delete_job(
        db: AsyncSession,
        job_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """删除任务"""
        job = await JobService.get_job_by_id(db, job_id, owner_id)
        if not job:
            return False

        # 只能删除未开始或已完成的任务
        if job.status in ["running", "scheduled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="正在运行或已调度的任务不能删除"
            )

        await db.delete(job)
        await db.commit()

        return True

    @staticmethod
    async def pause_job(
        db: AsyncSession,
        job_id: uuid.UUID,
        reason: Optional[str] = None,
        owner_id: Optional[uuid.UUID] = None,
    ) -> Job:
        """暂停任务"""
        job = await JobService.get_job_by_id(db, job_id, owner_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="任务不存在"
            )

        if job.status not in ["scheduled", "running", "retrying"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无法暂停状态为 {job.status} 的任务"
            )

        # TODO: 调用 Layer 0 Orchestrator 暂停任务
        job.status = "waiting"
        job.error_message = reason or "任务已暂停"
        job.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(job)

        return job

    @staticmethod
    async def resume_job(
        db: AsyncSession,
        job_id: uuid.UUID,
        reason: Optional[str] = None,
        owner_id: Optional[uuid.UUID] = None,
    ) -> Job:
        """恢复任务"""
        job = await JobService.get_job_by_id(db, job_id, owner_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="任务不存在"
            )

        if job.status != "waiting":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无法恢复状态为 {job.status} 的任务"
            )

        # TODO: 调用 Layer 0 Orchestrator 恢复任务
        job.status = "scheduled"
        job.scheduled_at = datetime.utcnow()
        job.error_message = None
        job.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(job)

        return job

    @staticmethod
    async def cancel_job(
        db: AsyncSession,
        job_id: uuid.UUID,
        reason: Optional[str] = None,
        owner_id: Optional[uuid.UUID] = None,
    ) -> Job:
        """取消任务"""
        job = await JobService.get_job_by_id(db, job_id, owner_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="任务不存在"
            )

        if job.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无法取消状态为 {job.status} 的任务"
            )

        # TODO: 调用 Layer 0 Orchestrator 取消任务
        job.status = "cancelled"
        job.error_message = reason or "任务已取消"
        job.updated_at = datetime.utcnow()
        job.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(job)

        return job

    @staticmethod
    async def retry_job(
        db: AsyncSession,
        job_id: uuid.UUID,
        reason: Optional[str] = None,
        owner_id: Optional[uuid.UUID] = None,
    ) -> Job:
        """重试任务"""
        job = await JobService.get_job_by_id(db, job_id, owner_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="任务不存在"
            )

        if job.status != "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"只能重试失败的任务"
            )

        if job.retry_count >= job.max_retries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"已达到最大重试次数 ({job.max_retries})"
            )

        # TODO: 调用 Layer 0 Orchestrator 重试任务
        job.retry_count += 1
        job.status = "scheduled"
        job.scheduled_at = datetime.utcnow()
        job.error_message = None
        job.error_stack = None
        job.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(job)

        return job

    @staticmethod
    async def sync_job_status(
        db: AsyncSession,
        job_id: uuid.UUID,
        status: str,
        error_message: Optional[str] = None,
        output_artifacts: Optional[List[str]] = None,
    ) -> Job:
        """同步任务状态（供 Worker 或 Orchestrator 调用）"""
        job_result = await db.execute(select(Job).filter(Job.id == job_id))
        job = job_result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="任务不存在"
            )

        # 更新状态
        job.status = status
        job.updated_at = datetime.utcnow()

        if status == "running" and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status in ["completed", "failed", "cancelled"]:
            job.completed_at = datetime.utcnow()

        if error_message:
            job.error_message = error_message

        if output_artifacts:
            job.output_artifacts = output_artifacts

        await db.commit()
        await db.refresh(job)

        return job

    @staticmethod
    async def get_recent_jobs(
        db: AsyncSession,
        owner_id: Optional[uuid.UUID] = None,
        limit: int = 10,
    ) -> List[Job]:
        """获取最近的任务列表"""
        query = select(Job).order_by(desc(Job.created_at)).limit(limit)

        # 关联项目以验证所有权
        if owner_id:
            query = query.join(ProjectRecord).filter(ProjectRecord.created_by == owner_id)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_job_stats(
        db: AsyncSession,
        owner_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, int]:
        """获取任务统计信息"""
        # 构建基础查询
        query = select(Job.status)

        # 关联项目以验证所有权
        if owner_id:
            query = query.join(ProjectRecord).filter(ProjectRecord.created_by == owner_id)

        result = await db.execute(query)
        statuses = [row[0] for row in result.all()]

        # 统计各状态数量
        stats = {
            "total": len(statuses),
            "pending": statuses.count("pending"),
            "scheduled": statuses.count("scheduled"),
            "running": statuses.count("running"),
            "waiting": statuses.count("waiting"),
            "completed": statuses.count("completed"),
            "failed": statuses.count("failed"),
            "cancelled": statuses.count("cancelled"),
            "retrying": statuses.count("retrying"),
        }

        # 计算运行中（包括 retrying）的数量
        stats["active"] = stats["running"] + stats["retrying"]
        stats["finished"] = stats["completed"] + stats["failed"] + stats["cancelled"]

        return stats
