# ADR 0003: Artifact Registry 接口设计

## 状态

设计中

## 上下文

Artifact Registry 是模块间数据传递的核心组件。需要设计一个清晰的接口，支持：

1. 模块写入 Artifact
2. 模块读取 Artifact
3. 版本管理
4. 引用计数
5. 存储抽象

## 接口设计

### 核心 API

```python
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, IO
from dataclasses import dataclass
from enum import Enum
import uuid

class ArtifactType(Enum):
    """Artifact 类型"""
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    METADATA = "metadata"
    CHARACTER_DB = "character_db"
    VOICE_DB = "voice_db"
    DIALOGUE_TIMELINE = "dialogue_timeline"
    SCENE_TIMELINE = "scene_timeline"
    ANALYSIS_RESULT = "analysis_result"
    SYNTHESIS_CONFIG = "synthesis_config"
    FINAL_VIDEO = "final_video"
    QA_REPORT = "qa_report"
    ARCHIVE = "archive"
    LOG = "log"
    OTHER = "other"

class ArtifactStatus(Enum):
    """Artifact 状态"""
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"

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
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class ArtifactRef:
    """Artifact 引用"""
    id: uuid.UUID
    metadata: ArtifactMetadata
    storage_path: str
    version: int

class ArtifactStorage(ABC):
    """存储后端抽象"""

    @abstractmethod
    async def upload(
        self,
        artifact_id: uuid.UUID,
        data: IO[bytes],
        metadata: ArtifactMetadata
    ) -> str:
        """上传数据，返回存储路径"""
        pass

    @abstractmethod
    async def download(self, artifact_id: uuid.UUID) -> IO[bytes]:
        """下载数据"""
        pass

    @abstractmethod
    async def delete(self, artifact_id: uuid.UUID) -> None:
        """删除数据"""
        pass

    @abstractmethod
    async def exists(self, artifact_id: uuid.UUID) -> bool:
        """检查是否存在"""
        pass

    @abstractmethod
    async def get_size(self, artifact_id: uuid.UUID) -> int:
        """获取大小（字节）"""
        pass

class MinioStorage(ArtifactStorage):
    """MinIO 存储实现"""

    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self._client = None

    async def _get_client(self):
        """懒加载 MinIO 客户端"""
        if self._client is None:
            from minio import Minio
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=False
            )
        return self._client

    async def upload(
        self,
        artifact_id: uuid.UUID,
        data: IO[bytes],
        metadata: ArtifactMetadata
    ) -> str:
        client = await self._get_client()
        path = f"{metadata.project_id}/{artifact_id}/{metadata.name}"
        client.put_object(
            self.bucket,
            path,
            data,
            length=metadata.size_bytes or -1,
            content_type=metadata.mime_type
        )
        return path

    async def download(self, artifact_id: uuid.UUID) -> IO[bytes]:
        # 实现下载逻辑
        pass

    async def delete(self, artifact_id: uuid.UUID) -> None:
        # 实现删除逻辑
        pass

    async def exists(self, artifact_id: uuid.UUID) -> bool:
        # 实现存在检查
        pass

    async def get_size(self, artifact_id: uuid.UUID) -> int:
        # 实现大小获取
        pass

class ArtifactRegistry:
    """Artifact 注册表"""

    def __init__(
        self,
        db,  # SQLAlchemy Session
        storage: ArtifactStorage
    ):
        self.db = db
        self.storage = storage

    async def create(
        self,
        metadata: ArtifactMetadata,
        parent_artifact_id: Optional[uuid.UUID] = None
    ) -> ArtifactRef:
        """创建新 Artifact

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
            parent = await self.db.get(artifacts, parent_artifact_id)
            if parent:
                version = parent.version + 1

        # 创建数据库记录
        artifact = {
            "id": artifact_id,
            "name": metadata.name,
            "type": metadata.type.value,
            "status": ArtifactStatus.PENDING.value,
            "project_id": metadata.project_id,
            "job_id": metadata.job_id,
            "module_id": metadata.module_id,
            "storage_type": "minio",
            "storage_bucket": "filmdubbing-artifacts",
            "mime_type": metadata.mime_type,
            "metadata": metadata.metadata or {},
            "version": version,
            "parent_artifact_id": parent_artifact_id,
            "ref_count": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        await self.db.insert(artifacts, artifact)
        await self.db.commit()

        return ArtifactRef(
            id=artifact_id,
            metadata=metadata,
            storage_path=None,  # 上传后设置
            version=version
        )

    async def upload(
        self,
        artifact_id: uuid.UUID,
        data: IO[bytes]
    ) -> ArtifactRef:
        """上传 Artifact 数据

        Args:
            artifact_id: Artifact ID
            data: 数据流

        Returns:
            ArtifactRef: 更新后的引用
        """
        # 获取 Artifact 信息
        artifact = await self.db.get(artifacts, artifact_id)
        if not artifact:
            raise ValueError(f"Artifact {artifact_id} not found")

        # 更新状态
        await self.db.update(
            artifacts,
            artifact_id,
            {"status": ArtifactStatus.UPLOADING.value}
        )

        try:
            # 上传到存储
            metadata = ArtifactMetadata(
                name=artifact["name"],
                type=ArtifactType(artifact["type"]),
                project_id=artifact["project_id"],
                mime_type=artifact["mime_type"],
                size_bytes=artifact.get("size_bytes")
            )

            storage_path = await self.storage.upload(artifact_id, data, metadata)

            # 更新数据库
            checksum = await self._calculate_checksum(data)
            size = await self.storage.get_size(artifact_id)

            await self.db.update(
                artifacts,
                artifact_id,
                {
                    "status": ArtifactStatus.READY.value,
                    "storage_path": storage_path,
                    "checksum": checksum,
                    "size_bytes": size,
                    "updated_at": datetime.utcnow(),
                    "accessed_at": datetime.utcnow()
                }
            )

            await self.db.commit()

            return ArtifactRef(
                id=artifact_id,
                metadata=metadata,
                storage_path=storage_path,
                version=artifact["version"]
            )

        except Exception as e:
            await self.db.update(
                artifacts,
                artifact_id,
                {"status": ArtifactStatus.FAILED.value}
            )
            await self.db.commit()
            raise

    async def download(self, artifact_id: uuid.UUID) -> IO[bytes]:
        """下载 Artifact 数据

        Args:
            artifact_id: Artifact ID

        Returns:
            IO[bytes]: 数据流
        """
        # 更新访问时间
        await self.db.update(
            artifacts,
            artifact_id,
            {"accessed_at": datetime.utcnow()}
        )

        # 从存储下载
        return await self.storage.download(artifact_id)

    async def get(self, artifact_id: uuid.UUID) -> Optional[ArtifactRef]:
        """获取 Artifact 引用

        Args:
            artifact_id: Artifact ID

        Returns:
            Optional[ArtifactRef]: Artifact 引用或 None
        """
        artifact = await self.db.get(artifacts, artifact_id)
        if not artifact:
            return None

        return ArtifactRef(
            id=artifact["id"],
            metadata=ArtifactMetadata(
                name=artifact["name"],
                type=ArtifactType(artifact["type"]),
                project_id=artifact["project_id"],
                job_id=artifact.get("job_id"),
                module_id=artifact.get("module_id"),
                mime_type=artifact.get("mime_type"),
                size_bytes=artifact.get("size_bytes"),
                checksum=artifact.get("checksum"),
                metadata=artifact.get("metadata")
            ),
            storage_path=artifact.get("storage_path"),
            version=artifact["version"]
        )

    async def increment_ref(self, artifact_id: uuid.UUID) -> None:
        """增加引用计数"""
        artifact = await self.db.get(artifacts, artifact_id)
        if artifact:
            await self.db.update(
                artifacts,
                artifact_id,
                {"ref_count": artifact["ref_count"] + 1}
            )

    async def decrement_ref(self, artifact_id: uuid.UUID) -> None:
        """减少引用计数，如果为 0 则标记删除"""
        artifact = await self.db.get(artifacts, artifact_id)
        if artifact:
            new_count = artifact["ref_count"] - 1
            await self.db.update(
                artifacts,
                artifact_id,
                {"ref_count": max(0, new_count)}
            )

            # 如果引用计数为 0 且超过 30 天未访问，标记删除
            if new_count <= 0:
                last_access = artifact.get("accessed_at") or artifact["created_at"]
                if (datetime.utcnow() - last_access).days > 30:
                    await self.db.update(
                        artifacts,
                        artifact_id,
                        {"status": ArtifactStatus.ARCHIVED.value}
                    )

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        artifact_type: Optional[ArtifactType] = None
    ) -> List[ArtifactRef]:
        """列出项目的所有 Artifact

        Args:
            project_id: 项目 ID
            artifact_type: 可选的类型过滤

        Returns:
            List[ArtifactRef]: Artifact 引用列表
        """
        query = "SELECT * FROM artifacts WHERE project_id = $1"
        params = [project_id]

        if artifact_type:
            query += " AND type = $2"
            params.append(artifact_type.value)

        rows = await self.db.fetch(query, *params)

        return [
            ArtifactRef(
                id=row["id"],
                metadata=ArtifactMetadata(...),
                storage_path=row["storage_path"],
                version=row["version"]
            )
            for row in rows
        ]

    async def delete(self, artifact_id: uuid.UUID) -> None:
        """删除 Artifact（软删除）"""
        await self.db.update(
            artifacts,
            artifact_id,
            {"status": ArtifactStatus.ARCHIVED.value}
        )

        # 可选：物理删除存储中的数据
        # await self.storage.delete(artifact_id)

    def _calculate_checksum(self, data: IO[bytes]) -> str:
        """计算 SHA256 校验和"""
        import hashlib
        sha256 = hashlib.sha256()
        data.seek(0)
        for chunk in iter(lambda: data.read(4096), b""):
            sha256.update(chunk)
        return sha256.hexdigest()
```

### 使用示例

```python
# 创建 Artifact
metadata = ArtifactMetadata(
    name="original_video.mp4",
    type=ArtifactType.VIDEO,
    project_id=project_id,
    job_id=job_id,
    module_id="M01",
    mime_type="video/mp4",
    size_bytes=102400000
)

ref = await registry.create(metadata)

# 上传数据
with open("video.mp4", "rb") as f:
    await registry.upload(ref.id, f)

# 读取数据
data = await registry.download(ref.id)

# 增加引用（另一个 Job 需要这个 Artifact）
await registry.increment_ref(ref.id)

# 减少引用
await registry.decrement_ref(ref.id)

# 列出项目的所有视频 Artifacts
videos = await registry.list_by_project(project_id, ArtifactType.VIDEO)
```

## 版本控制策略

Artifact 支持版本控制：

1. **父子关系**: 通过 `parent_artifact_id` 建立版本链
2. **版本号**: 自动递增
3. **保留策略**:
   - 所有版本保留 30 天
   - 生产版本永久保留
   - 中间版本可选择性清理

## 存储后端扩展

支持多种存储后端：

1. **MinIO** (默认)
2. **本地文件系统**
3. **AWS S3**
4. **Azure Blob Storage**
5. **Google Cloud Storage**

通过实现 `ArtifactStorage` 接口扩展。

## 缓存策略

1. **元数据缓存**: 使用 Redis 缓存热点 Artifact 元数据
2. **数据缓存**: 对小型 Artifact（<10MB）可缓存到 Redis
3. **CDN**: 对频繁访问的视频 Artifact 使用 CDN

## 监控指标

1. **存储使用量**: 按项目、类型统计
2. **上传/下载速度**: P50, P95, P99
3. **错误率**: 上传失败率、下载失败率
4. **清理效率**: 可回收空间占比

## 后续决策

- 是否需要支持分片上传（大文件）
- 是否需要支持断点续传
- CDN 配置
