"""
Artifact Registry - 模块间数据传递的核心组件
"""
import uuid
import io
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Artifact,
    ArtifactType,
    ArtifactStatus,
)
from .storage import (
    ArtifactStorage,
    MinioStorage,
    LocalStorage,
    calculate_checksum,
)
from .config import orchestrator_settings


@dataclass
class ArtifactMetadata:
    """Artifact 元数据"""
    name: str
    type: ArtifactType
    project_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    module_id: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArtifactRef:
    """Artifact 引用"""
    id: uuid.UUID
    metadata: ArtifactMetadata
    storage_path: Optional[str] = None
    version: int = 1


class ArtifactRegistry:
    """Artifact 注册表"""

    def __init__(
        self,
        db: AsyncSession,
        storage: Optional[ArtifactStorage] = None
    ):
        """
        初始化 Artifact Registry

        Args:
            db: 数据库会话
            storage: 存储后端，默认使用 MinIO
        """
        self.db = db
        self.storage = storage or self._create_default_storage()

    def _create_default_storage(self) -> ArtifactStorage:
        """创建默认存储后端"""
        backend = orchestrator_settings.artifact_storage_backend
        if backend == "minio":
            return MinioStorage()
        if backend == "local":
            return LocalStorage()
        # auto: 仅当显式配置了 MinIO 端点（非默认 localhost:9000）时使用 MinIO，否则使用本地存储
        if orchestrator_settings.minio_endpoint and orchestrator_settings.minio_endpoint != "localhost:9000":
            return MinioStorage()
        return LocalStorage()

    async def create(
        self,
        metadata: ArtifactMetadata,
        parent_artifact_id: Optional[uuid.UUID] = None
    ) -> ArtifactRef:
        """
        创建新 Artifact

        Args:
            metadata: Artifact 元数据
            parent_artifact_id: 父 Artifact ID（用于版本控制）

        Returns:
            ArtifactRef: Artifact 引用
        """
        artifact_id = uuid.uuid4()

        # 计算版本号
        version = 1
        if parent_artifact_id:
            parent = await self.db.get(Artifact, parent_artifact_id)
            if parent:
                version = parent.version + 1

        # 创建数据库记录
        artifact = Artifact(
            id=artifact_id,
            name=metadata.name,
            type=metadata.type,
            status=ArtifactStatus.PENDING,
            project_id=metadata.project_id,
            job_id=metadata.job_id,
            module_id=metadata.module_id,
            storage_type="minio" if isinstance(self.storage, MinioStorage) else "local",
            storage_bucket=orchestrator_settings.minio_bucket if isinstance(self.storage, MinioStorage) else None,
            mime_type=metadata.mime_type,
            size_bytes=metadata.size_bytes,
            checksum=metadata.checksum,
            extra_metadata=metadata.extra_metadata,
            version=version,
            parent_artifact_id=parent_artifact_id,
            ref_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(artifact)
        await self.db.flush()

        return ArtifactRef(
            id=artifact_id,
            metadata=metadata,
            storage_path=None,  # 上传后设置
            version=version
        )

    async def upload(
        self,
        artifact_id: uuid.UUID,
        data: io.BytesIO
    ) -> ArtifactRef:
        """
        上传 Artifact 数据

        Args:
            artifact_id: Artifact ID
            data: 数据流

        Returns:
            ArtifactRef: 更新后的引用
        """
        # 获取 Artifact 信息
        result = await self.db.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        artifact = result.scalar_one_or_none()

        if not artifact:
            raise ValueError(f"Artifact {artifact_id} not found")

        # 更新状态为上传中
        await self.db.execute(
            update(Artifact)
            .where(Artifact.id == artifact_id)
            .values(status=ArtifactStatus.UPLOADING)
        )

        try:
            # 准备元数据
            metadata = {
                "project_id": str(artifact.project_id),
                "name": artifact.name,
                "mime_type": artifact.mime_type,
                "artifact_id": str(artifact_id),
            }
            if artifact.extra_metadata:
                metadata.update(artifact.extra_metadata)

            # 计算校验和
            checksum = calculate_checksum(data)

            # 上传到存储
            storage_path = await self.storage.upload(
                str(artifact_id),
                data,
                metadata
            )

            # 获取大小
            data.seek(0, io.SEEK_END)
            size = data.tell()
            data.seek(0)

            # 更新数据库
            await self.db.execute(
                update(Artifact)
                .where(Artifact.id == artifact_id)
                .values(
                    status=ArtifactStatus.READY,
                    storage_path=storage_path,
                    checksum=checksum,
                    size_bytes=size,
                    updated_at=datetime.utcnow(),
                    accessed_at=datetime.utcnow()
                )
            )

            await self.db.flush()

            # 返回更新的引用
            return ArtifactRef(
                id=artifact_id,
                metadata=ArtifactMetadata(
                    name=artifact.name,
                    type=artifact.type,
                    project_id=artifact.project_id,
                    job_id=artifact.job_id,
                    module_id=artifact.module_id,
                    mime_type=artifact.mime_type,
                    size_bytes=size,
                    checksum=checksum,
                    extra_metadata=artifact.extra_metadata or {}
                ),
                storage_path=storage_path,
                version=artifact.version
            )

        except Exception as e:
            # 失败，更新状态
            await self.db.execute(
                update(Artifact)
                .where(Artifact.id == artifact_id)
                .values(status=ArtifactStatus.FAILED)
            )
            await self.db.flush()
            raise RuntimeError(f"Failed to upload artifact {artifact_id}: {e}")

    async def download(self, artifact_id: uuid.UUID) -> io.BytesIO:
        """
        下载 Artifact 数据

        Args:
            artifact_id: Artifact ID

        Returns:
            IO[bytes]: 数据流
        """
        # 更新访问时间
        await self.db.execute(
            update(Artifact)
            .where(Artifact.id == artifact_id)
            .values(accessed_at=datetime.utcnow())
        )

        # 获取 Artifact 信息
        result = await self.db.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        artifact = result.scalar_one_or_none()

        if not artifact:
            raise ValueError(f"Artifact {artifact_id} not found")

        if artifact.status != ArtifactStatus.READY:
            raise ValueError(f"Artifact {artifact_id} is not ready (status: {artifact.status})")

        if not artifact.storage_path:
            raise ValueError(f"Artifact {artifact_id} has no storage path")

        # 从存储下载
        if isinstance(self.storage, MinioStorage):
            return await self.storage.download_by_path(artifact.storage_path)
        else:
            return await self.storage.download_by_path(artifact.storage_path)

    async def get(self, artifact_id: uuid.UUID) -> Optional[ArtifactRef]:
        """
        获取 Artifact 引用

        Args:
            artifact_id: Artifact ID

        Returns:
            Optional[ArtifactRef]: Artifact 引用或 None
        """
        result = await self.db.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        artifact = result.scalar_one_or_none()

        if not artifact:
            return None

        return ArtifactRef(
            id=artifact.id,
            metadata=ArtifactMetadata(
                name=artifact.name,
                type=artifact.type,
                project_id=artifact.project_id,
                job_id=artifact.job_id,
                module_id=artifact.module_id,
                mime_type=artifact.mime_type,
                size_bytes=artifact.size_bytes,
                checksum=artifact.checksum,
                extra_metadata=artifact.extra_metadata or {}
            ),
            storage_path=artifact.storage_path,
            version=artifact.version
        )

    async def increment_ref(self, artifact_id: uuid.UUID) -> None:
        """
        增加引用计数

        Args:
            artifact_id: Artifact ID
        """
        result = await self.db.execute(
            update(Artifact)
            .where(Artifact.id == artifact_id)
            .values(ref_count=Artifact.ref_count + 1)
        )

    async def decrement_ref(self, artifact_id: uuid.UUID) -> None:
        """
        减少引用计数，如果为 0 则标记删除

        Args:
            artifact_id: Artifact ID
        """
        # 获取当前引用计数
        result = await self.db.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        artifact = result.scalar_one_or_none()

        if not artifact:
            return

        new_count = max(0, artifact.ref_count - 1)

        await self.db.execute(
            update(Artifact)
            .where(Artifact.id == artifact_id)
            .values(ref_count=new_count)
        )

        # 如果引用计数为 0 且超过 30 天未访问，标记删除
        if new_count <= 0:
            last_access = artifact.accessed_at or artifact.created_at
            days_since_access = (datetime.utcnow() - last_access).days

            if days_since_access > 30:
                await self.db.execute(
                    update(Artifact)
                    .where(Artifact.id == artifact_id)
                    .values(status=ArtifactStatus.ARCHIVED)
                )

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        artifact_type: Optional[ArtifactType] = None
    ) -> List[ArtifactRef]:
        """
        列出项目的所有 Artifact

        Args:
            project_id: 项目 ID
            artifact_type: 可选的类型过滤

        Returns:
            List[ArtifactRef]: Artifact 引用列表
        """
        query = select(Artifact).where(Artifact.project_id == project_id)

        if artifact_type:
            query = query.where(Artifact.type == artifact_type)

        query = query.order_by(Artifact.created_at.desc())

        result = await self.db.execute(query)
        artifacts = result.scalars().all()

        return [
            ArtifactRef(
                id=a.id,
                metadata=ArtifactMetadata(
                    name=a.name,
                    type=a.type,
                    project_id=a.project_id,
                    job_id=a.job_id,
                    module_id=a.module_id,
                    mime_type=a.mime_type,
                    size_bytes=a.size_bytes,
                    checksum=a.checksum,
                    extra_metadata=a.extra_metadata or {}
                ),
                storage_path=a.storage_path,
                version=a.version
            )
            for a in artifacts
        ]

    async def delete(self, artifact_id: uuid.UUID) -> None:
        """
        删除 Artifact（软删除）

        Args:
            artifact_id: Artifact ID
        """
        await self.db.execute(
            update(Artifact)
            .where(Artifact.id == artifact_id)
            .values(status=ArtifactStatus.ARCHIVED)
        )

        # 可选：物理删除存储中的数据
        # result = await self.db.execute(
        #     select(Artifact).where(Artifact.id == artifact_id)
        # )
        # artifact = result.scalar_one_or_none()
        # if artifact and artifact.storage_path:
        #     if isinstance(self.storage, MinioStorage):
        #         await self.storage.delete_by_path(artifact.storage_path)

    async def generate_download_url(
        self,
        artifact_id: uuid.UUID,
        expires: int = 3600
    ) -> str:
        """
        生成下载 URL（预签名 URL）

        Args:
            artifact_id: Artifact ID
            expires: 过期时间（秒）

        Returns:
            下载 URL
        """
        result = await self.db.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        artifact = result.scalar_one_or_none()

        if not artifact:
            raise ValueError(f"Artifact {artifact_id} not found")

        if not artifact.storage_path:
            raise ValueError(f"Artifact {artifact_id} has no storage path")

        if isinstance(self.storage, MinioStorage):
            return self.storage.generate_presigned_url(artifact.storage_path, expires)
        else:
            # 本地存储不支持预签名 URL
            raise NotImplementedError("Presigned URLs not supported for local storage")
