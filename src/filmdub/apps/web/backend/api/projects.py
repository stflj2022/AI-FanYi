"""项目 API 端点"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.core.orchestrator_db import get_db_context
from filmdub.apps.web.backend.services.project_service import ProjectService
from filmdub.apps.web.backend.models import User
from filmdub.apps.web.backend.api.dependencies import get_current_active_user
from filmdub.apps.web.backend.api.schemas.project_schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_context),
):
    """创建项目"""
    project = await ProjectService.create_project(
        db=db,
        project_data=project_data,
        owner_id=current_user.id,
    )
    return ProjectResponse.model_validate(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str | None = Query(None, description="搜索关键词"),
    status: str | None = Query(None, description="状态筛选"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_context),
):
    """获取项目列表（支持分页、搜索和筛选）"""
    projects, total = await ProjectService.list_projects(
        db=db,
        owner_id=current_user.id,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
    )

    return ProjectListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[ProjectResponse.model_validate(p) for p in projects],
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_context),
):
    """获取项目详情"""
    project = await ProjectService.get_project_by_id(
        db=db,
        project_id=uuid.UUID(project_id),
        owner_id=current_user.id,
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在或无权访问",
        )

    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_context),
):
    """更新项目"""
    project = await ProjectService.update_project(
        db=db,
        project_id=uuid.UUID(project_id),
        project_data=project_data,
        owner_id=current_user.id,
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在或无权访问",
        )

    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_context),
):
    """删除项目"""
    success = await ProjectService.delete_project(
        db=db,
        project_id=uuid.UUID(project_id),
        owner_id=current_user.id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在或无权访问",
        )
