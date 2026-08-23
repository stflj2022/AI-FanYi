"""上传 API 测试"""
import io
import uuid
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from filmdub.core.orchestrator_db import Base, get_db
from filmdub.apps.web.backend.main import app
from filmdub.apps.web.backend.api.schemas.upload_schemas import UploadStatus, MediaType


# 测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_uploads.db"
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    """覆盖数据库依赖"""
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# 覆盖数据库依赖
app.dependency_overrides[get_db] = override_get_db

# 创建测试客户端
client = TestClient(app)


@pytest.fixture(scope="function")
async def setup_database():
    """设置测试数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    # 清理上传会话
    from filmdub.apps.web.backend.services.upload_service import get_upload_service
    upload_service = get_upload_service()
    upload_service._sessions.clear()


@pytest.fixture
def mock_minio():
    """模拟 MinIO 客户端"""
    with patch("filmdub.apps.web.backend.services.upload_service.Minio") as mock:
        mock_client = Mock()
        mock.return_value = mock_client
        mock_client.bucket_exists.return_value = True
        mock_client.fput_object.return_value = None
        yield mock_client


@pytest.fixture
def mock_ffprobe():
    """模拟 FFprobe"""
    with patch("subprocess.run") as mock:
        mock.return_value = Mock(
            stdout='{"format": {"duration": "120.5", "format_name": "mp4"}, "streams": []}',
            returncode=0,
        )
        yield mock


@pytest.mark.asyncio
class TestUploadAPI:
    """上传 API 测试"""

    async def test_upload_file_success(self, setup_database, mock_minio, mock_ffprobe):
        """测试成功上传文件"""
        # 创建测试文件
        file_content = b"fake video content" * 1000  # 约 18KB
        file = io.BytesIO(file_content)
        file.name = "test_video.mp4"

        response = client.post(
            "/api/v1/uploads",
            files={"file": ("test_video.mp4", file, "video/mp4")},
            data={"media_type": "video"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ready"
        assert data["filename"] == "test_video.mp4"
        assert data["file_size"] == len(file_content)
        assert data["media_type"] == "video"
        assert "id" in data

    async def test_upload_file_with_project(self, setup_database, mock_minio, mock_ffprobe):
        """测试关联项目的上传"""
        project_id = str(uuid.uuid4())
        file_content = b"fake video content" * 100
        file = io.BytesIO(file_content)
        file.name = "test_with_project.mp4"

        response = client.post(
            "/api/v1/uploads",
            files={"file": ("test_with_project.mp4", file, "video/mp4")},
            data={
                "media_type": "video",
                "project_id": project_id,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["project_id"] == project_id

    async def test_upload_unsupported_mime_type(self, setup_database):
        """测试不支持的 MIME 类型"""
        file = io.BytesIO(b"fake content")
        file.name = "test.exe"

        response = client.post(
            "/api/v1/uploads",
            files={"file": ("test.exe", file, "application/octet-stream")},
            data={"media_type": "video"},
        )

        assert response.status_code == 415
        assert "不支持的文件类型" in response.json()["detail"]

    async def test_get_upload_progress(self, setup_database, mock_minio, mock_ffprobe):
        """测试获取上传进度"""
        # 先上传一个文件
        file_content = b"fake video content" * 100
        file = io.BytesIO(file_content)
        file.name = "test_progress.mp4"

        upload_response = client.post(
            "/api/v1/uploads",
            files={"file": ("test_progress.mp4", file, "video/mp4")},
            data={"media_type": "video"},
        )

        upload_id = upload_response.json()["id"]

        # 获取进度
        response = client.get(f"/api/v1/uploads/{upload_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["progress"] == 100.0
        assert data["bytes_uploaded"] == len(file_content)

    async def test_get_upload_progress_not_found(self, setup_database):
        """测试获取不存在的上传进度"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/uploads/{fake_id}")

        assert response.status_code == 404

    async def test_get_media_metadata(self, setup_database, mock_minio, mock_ffprobe):
        """测试获取媒体元数据"""
        # 先上传一个文件
        file_content = b"fake video content" * 100
        file = io.BytesIO(file_content)
        file.name = "test_metadata.mp4"

        upload_response = client.post(
            "/api/v1/uploads",
            files={"file": ("test_metadata.mp4", file, "video/mp4")},
            data={"media_type": "video"},
        )

        upload_id = upload_response.json()["id"]

        # 获取元数据
        response = client.get(f"/api/v1/uploads/{upload_id}/metadata")

        assert response.status_code == 200
        data = response.json()
        assert "media_asset_id" in data
        assert "filename" in data
        assert data["filename"] == "test_metadata.mp4"

    async def test_delete_upload_session(self, setup_database, mock_minio, mock_ffprobe):
        """测试删除上传会话"""
        # 先上传一个文件
        file_content = b"fake video content" * 100
        file = io.BytesIO(file_content)
        file.name = "test_delete.mp4"

        upload_response = client.post(
            "/api/v1/uploads",
            files={"file": ("test_delete.mp4", file, "video/mp4")},
            data={"media_type": "video"},
        )

        upload_id = upload_response.json()["id"]

        # 删除会话
        response = client.delete(f"/api/v1/uploads/{upload_id}")

        assert response.status_code == 204

        # 验证会话已删除
        response = client.get(f"/api/v1/uploads/{upload_id}")
        assert response.status_code == 404


class TestUploadService:
    """上传服务测试"""

    def test_create_session(self):
        """测试创建上传会话"""
        from filmdub.apps.web.backend.services.upload_service import get_upload_service

        service = get_upload_service()
        session = service.create_session(
            filename="test.mp4",
            file_size=1024 * 1024,
            mime_type="video/mp4",
            media_type=MediaType.VIDEO,
        )

        assert session.filename == "test.mp4"
        assert session.file_size == 1024 * 1024
        assert session.status == UploadStatus.PENDING
        assert session.progress == 0.0
        assert session.id is not None

    def test_update_progress(self):
        """测试更新进度"""
        from filmdub.apps.web.backend.services.upload_service import get_upload_service

        service = get_upload_service()
        session = service.create_session(
            filename="test.mp4",
            file_size=1000,
            mime_type="video/mp4",
            media_type=MediaType.VIDEO,
        )

        session.start_uploading("/tmp/test.mp4")
        session.update_progress(500)

        assert session.progress == 50.0
        assert session.bytes_uploaded == 500
        assert session.status == UploadStatus.UPLOADING

    def test_mark_ready(self):
        """测试标记为就绪"""
        from filmdub.apps.web.backend.services.upload_service import get_upload_service

        service = get_upload_service()
        session = service.create_session(
            filename="test.mp4",
            file_size=1000,
            mime_type="video/mp4",
            media_type=MediaType.VIDEO,
        )

        session.mark_ready("media-asset-123")

        assert session.status == UploadStatus.READY
        assert session.progress == 100.0
        assert session.media_asset_id == "media-asset-123"

    def test_mark_failed(self):
        """测试标记为失败"""
        from filmdub.apps.web.backend.services.upload_service import get_upload_service

        service = get_upload_service()
        session = service.create_session(
            filename="test.mp4",
            file_size=1000,
            mime_type="video/mp4",
            media_type=MediaType.VIDEO,
        )

        session.mark_failed("Network error")

        assert session.status == UploadStatus.FAILED
        assert session.error_message == "Network error"

    def test_cleanup_session(self):
        """测试清理会话"""
        from filmdub.apps.web.backend.services.upload_service import get_upload_service

        service = get_upload_service()
        session = service.create_session(
            filename="test.mp4",
            file_size=1000,
            mime_type="video/mp4",
            media_type=MediaType.VIDEO,
        )

        upload_id = session.id
        service.cleanup_session(upload_id)

        assert service.get_session(upload_id) is None
