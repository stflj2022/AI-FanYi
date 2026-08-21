"""
存储抽象层

支持多种存储后端：MinIO, Local, S3, etc.
"""
from abc import ABC, abstractmethod
from typing import IO, Optional
from pathlib import Path
import hashlib
import io

from minio import Minio
from minio.error import S3Error

from .config import orchestrator_settings


class ArtifactStorage(ABC):
    """存储后端抽象接口"""

    @abstractmethod
    async def upload(
        self,
        artifact_id: str,
        data: IO[bytes],
        metadata: dict
    ) -> str:
        """上传数据，返回存储路径

        Args:
            artifact_id: Artifact ID
            data: 数据流
            metadata: 元数据

        Returns:
            存储路径
        """
        pass

    @abstractmethod
    async def download(self, artifact_id: str) -> IO[bytes]:
        """下载数据

        Args:
            artifact_id: Artifact ID

        Returns:
            数据流
        """
        pass

    @abstractmethod
    async def delete(self, artifact_id: str) -> None:
        """删除数据

        Args:
            artifact_id: Artifact ID
        """
        pass

    @abstractmethod
    async def exists(self, artifact_id: str) -> bool:
        """检查是否存在

        Args:
            artifact_id: Artifact ID

        Returns:
            是否存在
        """
        pass

    @abstractmethod
    async def get_size(self, artifact_id: str) -> int:
        """获取大小（字节）

        Args:
            artifact_id: Artifact ID

        Returns:
            大小（字节）
        """
        pass


class MinioStorage(ArtifactStorage):
    """MinIO 存储实现"""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket: Optional[str] = None,
        secure: bool = False
    ):
        """
        初始化 MinIO 存储

        Args:
            endpoint: MinIO 端点 (host:port)
            access_key: 访问密钥
            secret_key: 密钥
            bucket: 存储桶名称
            secure: 是否使用 HTTPS
        """
        self.endpoint = endpoint or orchestrator_settings.minio_endpoint
        self.access_key = access_key or orchestrator_settings.minio_access_key
        self.secret_key = secret_key or orchestrator_settings.minio_secret_key
        self.bucket = bucket or orchestrator_settings.minio_bucket
        self.secure = secure or orchestrator_settings.minio_secure
        self._client: Optional[Minio] = None

    def _get_client(self) -> Minio:
        """获取 MinIO 客户端（懒加载）"""
        if self._client is None:
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
        return self._client

    async def _ensure_bucket(self) -> None:
        """确保存储桶存在"""
        client = self._get_client()
        try:
            if not client.bucket_exists(self.bucket):
                client.make_bucket(self.bucket)
        except S3Error as e:
            raise RuntimeError(f"Failed to ensure bucket {self.bucket}: {e}")

    async def upload(
        self,
        artifact_id: str,
        data: IO[bytes],
        metadata: dict
    ) -> str:
        """上传数据到 MinIO"""
        await self._ensure_bucket()
        client = self._get_client()

        # 构造存储路径
        project_id = metadata.get("project_id", "unknown")
        path = f"{project_id}/{artifact_id}/{metadata.get('name', 'artifact')}"

        # 读取数据以计算大小
        data.seek(0)
        content = data.read()
        size = len(content)
        data.seek(0)

        try:
            client.put_object(
                self.bucket,
                path,
                io.BytesIO(content),
                length=size,
                content_type=metadata.get("mime_type", "application/octet-stream"),
                metadata={k: str(v) for k, v in metadata.items()}
            )
            return path
        except S3Error as e:
            raise RuntimeError(f"Failed to upload artifact {artifact_id}: {e}")

    async def download(self, artifact_id: str) -> IO[bytes]:
        """从 MinIO 下载数据"""
        client = self._get_client()

        # 构造路径 (需要从数据库获取)
        # 这里简化处理，调用者需要提供完整路径
        # 实际使用时，应该从 artifact 记录中读取 storage_path

        # 这个方法需要重构，应该接收 path 而不是 artifact_id
        # 暂时抛出异常，建议使用 download_by_path
        raise NotImplementedError(
            "Use download_by_path() instead. This method needs refactoring."
        )

    async def download_by_path(self, path: str) -> IO[bytes]:
        """通过路径下载数据

        Args:
            path: 存储路径

        Returns:
            数据流
        """
        client = self._get_client()

        try:
            response = client.get_object(self.bucket, path)
            return io.BytesIO(response.read())
        except S3Error as e:
            raise RuntimeError(f"Failed to download artifact at {path}: {e}")

    async def delete(self, artifact_id: str) -> None:
        """删除 MinIO 中的数据"""
        # 同样需要 path
        raise NotImplementedError(
            "Use delete_by_path() instead. This method needs refactoring."
        )

    async def delete_by_path(self, path: str) -> None:
        """通过路径删除数据

        Args:
            path: 存储路径
        """
        client = self._get_client()

        try:
            client.remove_object(self.bucket, path)
        except S3Error as e:
            # 忽略对象不存在的错误
            if e.code != "NoSuchKey":
                raise RuntimeError(f"Failed to delete artifact at {path}: {e}")

    async def exists(self, artifact_id: str) -> bool:
        """检查 Artifact 是否存在"""
        # 需要重构
        raise NotImplementedError(
            "Use exists_by_path() instead. This method needs refactoring."
        )

    async def exists_by_path(self, path: str) -> bool:
        """通过路径检查是否存在

        Args:
            path: 存储路径

        Returns:
            是否存在
        """
        client = self._get_client()

        try:
            client.stat_object(self.bucket, path)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise RuntimeError(f"Failed to check artifact at {path}: {e}")

    async def get_size(self, artifact_id: str) -> int:
        """获取 Artifact 大小"""
        # 需要重构
        raise NotImplementedError(
            "Use get_size_by_path() instead. This method needs refactoring."
        )

    async def get_size_by_path(self, path: str) -> int:
        """通过路径获取大小

        Args:
            path: 存储路径

        Returns:
            大小（字节）
        """
        client = self._get_client()

        try:
            stat = client.stat_object(self.bucket, path)
            return stat.size
        except S3Error as e:
            raise RuntimeError(f"Failed to get size of artifact at {path}: {e}")

    def generate_presigned_url(
        self,
        path: str,
        expires: int = 3600
    ) -> str:
        """生成预签名 URL

        Args:
            path: 存储路径
            expires: 过期时间（秒）

        Returns:
            预签名 URL
        """
        client = self._get_client()

        try:
            return client.presigned_get_object(
                self.bucket,
                path,
                expires=expires
            )
        except S3Error as e:
            raise RuntimeError(f"Failed to generate presigned URL for {path}: {e}")


class LocalStorage(ArtifactStorage):
    """本地文件系统存储实现（用于开发和测试）"""

    def __init__(self, base_path: str = "./artifacts"):
        """
        初始化本地存储

        Args:
            base_path: 基础路径
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload(
        self,
        artifact_id: str,
        data: IO[bytes],
        metadata: dict
    ) -> str:
        """上传数据到本地文件系统"""
        project_id = metadata.get("project_id", "unknown")
        filename = metadata.get("name", "artifact")

        # 构造路径
        artifact_dir = self.base_path / project_id / artifact_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        file_path = artifact_dir / filename

        # 写入文件
        with open(file_path, "wb") as f:
            data.seek(0)
            f.write(data.read())

        return str(file_path.relative_to(self.base_path))

    async def download(self, artifact_id: str) -> IO[bytes]:
        """从本地文件系统下载数据"""
        # 需要重构，使用 download_by_path
        raise NotImplementedError(
            "Use download_by_path() instead. This method needs refactoring."
        )

    async def download_by_path(self, path: str) -> IO[bytes]:
        """通过路径下载数据"""
        file_path = self.base_path / path
        if not file_path.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")

        with open(file_path, "rb") as f:
            return io.BytesIO(f.read())

    async def delete(self, artifact_id: str) -> None:
        """删除本地文件"""
        raise NotImplementedError(
            "Use delete_by_path() instead. This method needs refactoring."
        )

    async def delete_by_path(self, path: str) -> None:
        """通过路径删除文件"""
        file_path = self.base_path / path
        if file_path.exists():
            file_path.unlink()

    async def exists(self, artifact_id: str) -> None:
        """检查是否存在"""
        raise NotImplementedError(
            "Use exists_by_path() instead. This method needs refactoring."
        )

    async def exists_by_path(self, path: str) -> bool:
        """通过路径检查是否存在"""
        file_path = self.base_path / path
        return file_path.exists()

    async def get_size(self, artifact_id: str) -> int:
        """获取大小"""
        raise NotImplementedError(
            "Use get_size_by_path() instead. This method needs refactoring."
        )

    async def get_size_by_path(self, path: str) -> int:
        """通过路径获取大小"""
        file_path = self.base_path / path
        if not file_path.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")
        return file_path.stat().st_size


def calculate_checksum(data: IO[bytes]) -> str:
    """计算 SHA256 校验和

    Args:
        data: 数据流

    Returns:
        十六进制校验和
    """
    sha256 = hashlib.sha256()
    data.seek(0)
    for chunk in iter(lambda: data.read(4096), b""):
        sha256.update(chunk)
    return sha256.hexdigest()
