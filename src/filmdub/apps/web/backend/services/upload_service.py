"""上传服务"""
import asyncio
import hashlib
import json
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

import aiofiles
from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from filmdub.core.models import MediaAsset, MediaStream
from filmdub.core.orchestrator_db import get_db_context


class UploadStatus(str, Enum):
    """上传状态"""
    PENDING = "pending"
    UPLOADING = "uploading"
    READY = "ready"
    FAILED = "failed"


class MediaType(str, Enum):
    """媒体类型"""
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"


class UploadSession:
    """上传会话管理"""

    def __init__(
        self,
        upload_id: uuid.UUID,
        filename: str,
        file_size: int,
        mime_type: str,
        project_id: Optional[uuid.UUID] = None,
        media_type: MediaType = MediaType.VIDEO,
    ):
        self.id = upload_id
        self.filename = filename
        self.file_size = file_size
        self.mime_type = mime_type
        self.project_id = project_id
        self.media_type = media_type
        self.status = UploadStatus.PENDING
        self.progress = 0.0
        self.bytes_uploaded = 0
        self.speed = 0.0
        self.estimated_remaining = None
        self.error_message = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self._upload_start_time: Optional[datetime] = None
        self._temp_path: Optional[str] = None

    def start_uploading(self, temp_path: str):
        """开始上传"""
        self.status = UploadStatus.UPLOADING
        self._temp_path = temp_path
        self._upload_start_time = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def update_progress(self, bytes_uploaded: int):
        """更新上传进度"""
        self.bytes_uploaded = bytes_uploaded
        self.progress = (bytes_uploaded / self.file_size) * 100 if self.file_size > 0 else 0

        # 计算速度和剩余时间
        if self._upload_start_time:
            elapsed = (datetime.utcnow() - self._upload_start_time).total_seconds()
            if elapsed > 0:
                self.speed = bytes_uploaded / elapsed
                remaining_bytes = self.file_size - bytes_uploaded
                if self.speed > 0:
                    self.estimated_remaining = remaining_bytes / self.speed

        self.updated_at = datetime.utcnow()

    def mark_ready(self, media_asset_id: str):
        """标记为就绪"""
        self.status = UploadStatus.READY
        self.progress = 100.0
        self.bytes_uploaded = self.file_size
        self.media_asset_id = media_asset_id
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error_message: str):
        """标记为失败"""
        self.status = UploadStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.utcnow()


class UploadService:
    """上传服务"""

    def __init__(
        self,
        minio_endpoint: str = "localhost:9000",
        minio_access_key: str = "minioadmin",
        minio_secret_key: str = "minioadmin",
        minio_secure: bool = False,
        minio_bucket: str = "filmdub-uploads",
        temp_upload_dir: str = "/tmp/filmdub-uploads",
    ):
        self.minio_endpoint = minio_endpoint
        self.minio_access_key = minio_access_key
        self.minio_secret_key = minio_secret_key
        self.minio_secure = minio_secure
        self.minio_bucket = minio_bucket
        self.temp_upload_dir = Path(temp_upload_dir)
        self.temp_upload_dir.mkdir(parents=True, exist_ok=True)

        # 上传会话存储
        self._sessions: Dict[uuid.UUID, UploadSession] = {}

        # 初始化 MinIO 客户端
        self._minio_client: Optional[Minio] = None

    @property
    def minio_client(self) -> Minio:
        """获取 MinIO 客户端（懒加载）"""
        if self._minio_client is None:
            self._minio_client = Minio(
                self.minio_endpoint,
                access_key=self.minio_access_key,
                secret_key=self.minio_secret_key,
                secure=self.minio_secure,
            )
            # 确保 bucket 存在
            if not self._minio_client.bucket_exists(self.minio_bucket):
                self._minio_client.make_bucket(self.minio_bucket)
        return self._minio_client

    def get_session(self, upload_id: uuid.UUID) -> Optional[UploadSession]:
        """获取上传会话"""
        return self._sessions.get(upload_id)

    def create_session(
        self,
        filename: str,
        file_size: int,
        mime_type: str,
        project_id: Optional[uuid.UUID] = None,
        media_type: MediaType = MediaType.VIDEO,
    ) -> UploadSession:
        """创建上传会话"""
        upload_id = uuid.uuid4()
        session = UploadSession(
            upload_id=upload_id,
            filename=filename,
            file_size=file_size,
            mime_type=mime_type,
            project_id=project_id,
            media_type=media_type,
        )
        self._sessions[upload_id] = session
        return session

    async def handle_upload(
        self,
        session: UploadSession,
        file: UploadFile,
        chunk_size: int = 8 * 1024 * 1024,  # 8MB chunks
    ) -> str:
        """处理文件上传"""
        # 创建临时文件
        temp_path = self.temp_upload_dir / f"{session.id}_{session.filename}"
        session.start_uploading(str(temp_path))

        try:
            async with aiofiles.open(temp_path, "wb") as f:
                bytes_uploaded = 0
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    await f.write(chunk)
                    bytes_uploaded += len(chunk)
                    session.update_progress(bytes_uploaded)

            # 计算文件哈希
            file_hash = await self._compute_file_hash(temp_path)

            # 上传到 MinIO（同步操作）
            object_name = f"{session.project_id or 'no-project'}/{session.id}/{session.filename}"
            self.minio_client.fput_object(
                self.minio_bucket,
                object_name,
                str(temp_path),
            )

            # 提取视频元数据
            metadata = await self._extract_metadata(temp_path)

            # 创建 Media Asset 记录（异步）
            media_asset_id = await self._create_media_asset(
                session=session,
                object_name=object_name,
                file_hash=file_hash,
                metadata=metadata,
            )

            session.mark_ready(media_asset_id)

            return media_asset_id

        except Exception as e:
            session.mark_failed(str(e))
            raise

        finally:
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()

    async def _compute_file_hash(self, file_path: Path) -> str:
        """计算文件 SHA256 哈希"""
        sha256_hash = hashlib.sha256()
        async with aiofiles.open(file_path, "rb") as f:
            async for chunk in f:
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    async def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """使用 FFprobe 提取媒体元数据"""
        try:
            # 在线程池中运行 FFprobe
            import subprocess
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [
                        "ffprobe",
                        "-v", "quiet",
                        "-print_format", "json",
                        "-show_format",
                        "-show_streams",
                        str(file_path),
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
            )
            metadata = json.loads(result.stdout)
            return metadata
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
            # FFprobe 不可用或出错，返回空元数据
            return {"format": {}, "streams": []}

    async def _create_media_asset(
        self,
        session: UploadSession,
        object_name: str,
        file_hash: str,
        metadata: Dict[str, Any],
    ) -> str:
        """创建 Media Asset 记录"""
        async with get_db_context() as db:
            try:
                # 从元数据中提取信息
                format_info = metadata.get("format", {})
                duration_seconds = float(format_info.get("duration", 0)) or None
                container_format = format_info.get("format_name")

                # 解析流信息
                streams = metadata.get("streams", [])
                video_streams = [s for s in streams if s.get("codec_type") == "video"]
                audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
                subtitle_streams = [s for s in streams if s.get("codec_type") == "subtitle"]

                # 创建 Media Asset 记录
                media_asset_id = str(uuid.uuid4())
                media_asset = MediaAsset(
                    id=media_asset_id,
                    episode_id=None,  # 可以后续关联
                    original_filename=session.filename,
                    storage_path=object_name,
                    file_size=session.file_size,
                    sha256=file_hash,
                    duration_seconds=duration_seconds,
                    container_format=container_format,
                    status="READY",
                )
                db.add(media_asset)
                await db.flush()

                # 创建流记录
                for stream in streams:
                    stream_id = str(uuid.uuid4())
                    stream_type = stream.get("codec_type", "unknown")

                    # 只有 MediaStream 模型存在时才创建
                    try:
                        media_stream = MediaStream(
                            id=stream_id,
                            media_id=media_asset_id,
                            stream_type=stream_type,
                            index=stream.get("index", 0),
                            codec=stream.get("codec_name"),
                            codec_long=stream.get("codec_long_name"),
                            profile=stream.get("profile"),
                            level=stream.get("level"),
                            width=stream.get("width"),
                            height=stream.get("height"),
                            frame_rate=stream.get("r_frame_rate"),
                            bit_rate=stream.get("bit_rate"),
                            channels=stream.get("channels"),
                            sample_rate=stream.get("sample_rate"),
                            language=stream.get("tags", {}).get("language"),
                        )
                        db.add(media_stream)
                    except Exception:
                        pass  # MediaStream 模型可能不存在

                await db.commit()

                return media_asset_id

            except Exception as e:
                await db.rollback()
                raise HTTPException(status_code=500, detail=f"创建媒体资产记录失败: {str(e)}")

    def cleanup_session(self, upload_id: uuid.UUID):
        """清理上传会话"""
        self._sessions.pop(upload_id, None)


# 全局上传服务实例
_upload_service: Optional[UploadService] = None


def get_upload_service() -> UploadService:
    """获取上传服务实例"""
    global _upload_service
    if _upload_service is None:
        # 从环境变量读取配置
        _upload_service = UploadService(
            minio_endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            minio_access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            minio_secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            minio_secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
            minio_bucket=os.getenv("MINIO_BUCKET", "filmdub-uploads"),
            temp_upload_dir=os.getenv("TEMP_UPLOAD_DIR", "/tmp/filmdub-uploads"),
        )
    return _upload_service
