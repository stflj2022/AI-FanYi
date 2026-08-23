"""
项目管理服务
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, and_
from sqlalchemy.orm import selectinload
import uuid

from filmdub.core.models import WebProject as ProjectRecord, ProjectStatus as CoreProjectStatus
from filmdub.apps.web.backend.api.schemas.project_schemas import ProjectCreate, ProjectUpdate

# 兼容性别名
ProjectStatus = CoreProjectStatus


class ProjectService:
    """项目管理服务"""

    @staticmethod
    async def create_project(
        db: AsyncSession,
        project_data: ProjectCreate,
        owner_id: Optional[uuid.UUID] = None,
    ) -> ProjectRecord:
        """
        创建项目

        Args:
            db: 数据库会话
            project_data: 项目数据
            owner_id: 创建用户 ID

        Returns:
            创建的项目对象
        """
        project = ProjectRecord(
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
            created_by=owner_id,
            config=project_data.config or {},
        )

        db.add(project)
        await db.commit()
        await db.refresh(project)

        return project

    @staticmethod
    async def get_project_by_id(
        db: AsyncSession,
        project_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
        load_relations: bool = True,
    ) -> Optional[ProjectRecord]:
        """
        根据 ID 获取项目

        Args:
            db: 数据库会话
            project_id: 项目 ID
            owner_id: 所有者 ID（验证权限）
            load_relations: 是否加载关联数据

        Returns:
            项目对象或 None
        """
        query = select(ProjectRecord).where(ProjectRecord.id == project_id)

        if owner_id:
            query = query.where(ProjectRecord.created_by == owner_id)

        if load_relations:
            query = query.options(
                selectinload(ProjectRecord.jobs),
                selectinload(ProjectRecord.characters),
            )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_projects(
        db: AsyncSession,
        owner_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
        status: Optional[ProjectStatus] = None,
        search: Optional[str] = None,
    ) -> tuple[List[ProjectRecord], int]:
        """
        获取项目列表（支持分页、搜索和筛选）

        Args:
            db: 数据库会话
            owner_id: 所有者 ID（过滤用户自己的项目）
            page: 页码（从 1 开始）
            page_size: 每页数量
            status: 项目状态（过滤）
            search: 搜索关键词（搜索名称、标题、描述）

        Returns:
            (项目列表, 总数)
        """
        query = select(ProjectRecord)

        # 统计查询
        count_query = select(func.count(ProjectRecord.id))

        # 应用过滤条件
        conditions = []

        if owner_id:
            conditions.append(ProjectRecord.created_by == owner_id)

        if status:
            conditions.append(ProjectRecord.status == status)

        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    ProjectRecord.name.ilike(search_pattern),
                    ProjectRecord.title.ilike(search_pattern),
                    ProjectRecord.description.ilike(search_pattern),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # 统计总数
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页和排序
        skip = (page - 1) * page_size
        query = (
            query
            .order_by(desc(ProjectRecord.created_at))
            .offset(skip)
            .limit(page_size)
        )

        # 执行查询
        result = await db.execute(query)
        projects = result.scalars().all()

        return list(projects), total

    @staticmethod
    async def update_project(
        db: AsyncSession,
        project_id: uuid.UUID,
        project_data: ProjectUpdate,
        owner_id: Optional[uuid.UUID] = None,
    ) -> Optional[ProjectRecord]:
        """
        更新项目

        Args:
            db: 数据库会话
            project_id: 项目 ID
            project_data: 更新数据
            owner_id: 所有者 ID（验证权限）

        Returns:
            更新后的项目对象或 None
        """
        from datetime import datetime

        project = await ProjectService.get_project_by_id(db, project_id, owner_id, load_relations=False)

        if not project:
            return None

        # 更新字段
        update_data = project_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(project, key):
                setattr(project, key, value)

        # 更新时间戳
        project.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(project)

        return project

    @staticmethod
    async def delete_project(
        db: AsyncSession,
        project_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """
        删除项目

        Args:
            db: 数据库会话
            project_id: 项目 ID
            owner_id: 所有者 ID（验证权限）

        Returns:
            是否删除成功
        """
        project = await ProjectService.get_project_by_id(db, project_id, owner_id, load_relations=False)

        if not project:
            return False

        await db.delete(project)
        await db.commit()

        return True

    @staticmethod
    async def update_project_status(
        db: AsyncSession,
        project_id: uuid.UUID,
        status: ProjectStatus,
    ) -> Optional[ProjectRecord]:
        """
        更新项目状态

        Args:
            db: 数据库会话
            project_id: 项目 ID
            status: 新状态

        Returns:
            更新后的项目对象或 None
        """
        from datetime import datetime

        project = await ProjectService.get_project_by_id(db, project_id, load_relations=False)

        if not project:
            return None

        project.status = status
        project.updated_at = datetime.utcnow()

        if status == ProjectStatus.COMPLETED:
            project.completed_at = datetime.utcnow()
        elif status in (ProjectStatus.PROCESSING, ProjectStatus.INTAKE):
            project.started_at = project.started_at or datetime.utcnow()

        await db.commit()
        await db.refresh(project)

        return project
