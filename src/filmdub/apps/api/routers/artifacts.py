"""
Artifact 管理 API 路由

提供 Artifact 的创建/上传/下载/列表/删除，全部委托给 ArtifactRegistry
（Ticket 002 的真实实现），并为 Web 前端（Ticket 014）提供所需端点：
- GET  /api/v1/projects/{project_id}/artifacts
- POST /api/v1/artifacts/upload
- GET  /api/v1/artifacts/{artifact_id}
- GET  /api/v1/artifacts/{artifact_id}/download
- DELETE /api/v1/artifacts/{artifact_id}
"""
import io
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.orchestrator.database import get_db
from filmdub.orchestrator.models import Artifact, ArtifactType, ArtifactStatus, Project
from filmdub.orchestrator.artifact_registry import ArtifactMetadata, ArtifactRegistry
from filmdub.apps.api.schemas import (
    ArtifactCreate,
    ArtifactResponse,
    ArtifactListResponse,
)

router = APIRouter(tags=["artifacts"])


def _to_response(artifact: Artifact) -> ArtifactResponse:
    """将 ORM Artifact 转为响应模型。"""
    return ArtifactResponse(
        id=artifact.id,
        name=artifact.name,
        type=artifact.type.value if hasattr(artifact.type, "value") else str(artifact.type),
        status=artifact.status.value if hasattr(artifact.status, "value") else str(artifact.status),
        project_id=artifact.project_id,
        job_id=artifact.job_id,
        module_id=artifact.module_id,
        size_bytes=artifact.size_bytes,
        mime_type=artifact.mime_type,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
        accessed_at=artifact.accessed_at,
        version=artifact.version,
    )


@router.get("/projects/{project_id}/artifacts", response_model=List[ArtifactListResponse])
async def list_project_artifacts(
    project_id: uuid.UUID,
    artifact_type: Optional[str] = Query(None, alias="type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[ArtifactListResponse]:
    """列出项目的 Artifact。"""
    # 校验项目存在
    result = await db.execute(select(Project).where(Project.id == project_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    query = select(Artifact).where(Artifact.project_id == project_id)
    if artifact_type:
        try:
            type_enum = ArtifactType(artifact_type)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid artifact type: {artifact_type}")
        query = query.where(Artifact.type == type_enum)

    query = query.order_by(Artifact.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    artifacts = result.scalars().all()

    return [
        ArtifactListResponse(
            id=a.id,
            name=a.name,
            type=a.type.value if hasattr(a.type, "value") else str(a.type),
            status=a.status.value if hasattr(a.status, "value") else str(a.status),
            size_bytes=a.size_bytes,
            created_at=a.created_at,
        )
        for a in artifacts
    ]


@router.post("/artifacts", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    artifact_data: ArtifactCreate,
    db: AsyncSession = Depends(get_db),
) -> ArtifactResponse:
    """创建 Artifact 元数据记录。"""
    result = await db.execute(select(Project).where(Project.id == artifact_data.project_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {artifact_data.project_id} not found",
        )

    try:
        type_enum = ArtifactType(artifact_data.type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid artifact type: {artifact_data.type}")

    registry = ArtifactRegistry(db)
    ref = await registry.create(
        ArtifactMetadata(
            name=artifact_data.name,
            type=type_enum,
            project_id=artifact_data.project_id,
            job_id=artifact_data.job_id,
            module_id=artifact_data.module_id,
            mime_type=artifact_data.mime_type,
        )
    )
    artifact = await db.get(Artifact, ref.id)
    return _to_response(artifact)


@router.post("/artifacts/upload", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def upload_artifact(
    project_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    artifact_type: Optional[str] = Form(None),
    module_id: Optional[str] = Form(None),
    job_id: Optional[uuid.UUID] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> ArtifactResponse:
    """上传文件并创建 Artifact（真实写入存储后端）。"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    type_value = artifact_type or ArtifactType.OTHER.value
    try:
        type_enum = ArtifactType(type_value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid artifact type: {type_value}")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    registry = ArtifactRegistry(db)
    ref = await registry.create(
        ArtifactMetadata(
            name=name or file.filename or "upload.bin",
            type=type_enum,
            project_id=project_id,
            job_id=job_id,
            module_id=module_id,
            mime_type=file.content_type,
            size_bytes=len(content),
        )
    )
    await registry.upload(ref.id, io.BytesIO(content))

    artifact = await db.get(Artifact, ref.id)
    return _to_response(artifact)


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ArtifactResponse:
    """获取 Artifact 详情。"""
    artifact = await db.get(Artifact, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Artifact {artifact_id} not found")
    return _to_response(artifact)


@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """下载 Artifact 内容（从存储后端读取真实字节）。"""
    artifact = await db.get(Artifact, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Artifact {artifact_id} not found")

    registry = ArtifactRegistry(db)
    data = await registry.download(artifact_id)

    media_type = artifact.mime_type or "application/octet-stream"
    return StreamingResponse(
        data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.name}"',
            "Content-Length": str(artifact.size_bytes or 0),
        },
    )


@router.delete("/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """删除 Artifact（软删除为 archived）。"""
    artifact = await db.get(Artifact, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Artifact {artifact_id} not found")

    registry = ArtifactRegistry(db)
    await registry.delete(artifact_id)
    await db.flush()
