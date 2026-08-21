"""
Artifact Registry 测试
"""
import pytest
import uuid
import io

from sqlalchemy import select

from src.filmdub.orchestrator.database import get_db_context, Base, engine
from src.filmdub.orchestrator.models import (
    Artifact,
    Project,
    ArtifactType,
    ArtifactStatus,
)
from src.filmdub.orchestrator.artifact_registry import (
    ArtifactRegistry,
    ArtifactMetadata,
)
from src.filmdub.orchestrator.storage import LocalStorage, calculate_checksum


# pytest 配置
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_database(event_loop):
    """初始化测试数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_create_artifact(setup_database):
    """测试创建 Artifact"""
    async with get_db_context() as db:
        # 创建项目
        project = Project(
            name="Test Project",
            status="pending",
        )
        db.add(project)
        await db.flush()

        # 创建 Artifact Registry
        storage = LocalStorage(base_path="/tmp/test_artifacts")
        registry = ArtifactRegistry(db, storage)

        # 创建 Artifact 元数据
        metadata = ArtifactMetadata(
            name="test_file.txt",
            type=ArtifactType.METADATA,
            project_id=project.id,
            module_id="M01",
            mime_type="text/plain",
        )

        # 创建 Artifact
        ref = await registry.create(metadata)

        assert ref.id is not None
        assert ref.metadata.name == "test_file.txt"
        assert ref.metadata.type == ArtifactType.METADATA
        assert ref.version == 1

        await db.rollback()


@pytest.mark.asyncio
async def test_upload_artifact(setup_database):
    """测试上传 Artifact"""
    async with get_db_context() as db:
        # 创建项目
        project = Project(
            name="Test Project",
            status="pending",
        )
        db.add(project)
        await db.flush()

        # 创建 Artifact Registry
        storage = LocalStorage(base_path="/tmp/test_artifacts")
        registry = ArtifactRegistry(db, storage)

        # 创建 Artifact
        metadata = ArtifactMetadata(
            name="test_file.txt",
            type=ArtifactType.METADATA,
            project_id=project.id,
            module_id="M01",
            mime_type="text/plain",
        )

        ref = await registry.create(metadata)

        # 上传数据
        data = io.BytesIO(b"Hello, World!")
        updated_ref = await registry.upload(ref.id, data)

        assert updated_ref.storage_path is not None
        assert updated_ref.metadata.size_bytes == 13
        assert updated_ref.metadata.checksum is not None

        # 验证状态
        result = await db.execute(
            select(Artifact).where(Artifact.id == ref.id)
        )
        artifact = result.scalar_one()
        assert artifact.status == ArtifactStatus.READY

        await db.rollback()


@pytest.mark.asyncio
async def test_download_artifact(setup_database):
    """测试下载 Artifact"""
    async with get_db_context() as db:
        # 创建项目
        project = Project(
            name="Test Project",
            status="pending",
        )
        db.add(project)
        await db.flush()

        # 创建 Artifact Registry
        storage = LocalStorage(base_path="/tmp/test_artifacts")
        registry = ArtifactRegistry(db, storage)

        # 创建并上传 Artifact
        metadata = ArtifactMetadata(
            name="test_file.txt",
            type=ArtifactType.METADATA,
            project_id=project.id,
            module_id="M01",
            mime_type="text/plain",
        )

        ref = await registry.create(metadata)
        data = io.BytesIO(b"Hello, World!")
        await registry.upload(ref.id, data)

        # 下载 Artifact
        downloaded_data = await registry.download(ref.id)

        assert downloaded_data.read() == b"Hello, World!"

        await db.rollback()


@pytest.mark.asyncio
async def test_get_artifact(setup_database):
    """测试获取 Artifact 引用"""
    async with get_db_context() as db:
        # 创建项目
        project = Project(
            name="Test Project",
            status="pending",
        )
        db.add(project)
        await db.flush()

        # 创建 Artifact Registry
        storage = LocalStorage(base_path="/tmp/test_artifacts")
        registry = ArtifactRegistry(db, storage)

        # 创建并上传 Artifact
        metadata = ArtifactMetadata(
            name="test_file.txt",
            type=ArtifactType.METADATA,
            project_id=project.id,
            module_id="M01",
            mime_type="text/plain",
        )

        ref = await registry.create(metadata)
        data = io.BytesIO(b"Hello, World!")
        await registry.upload(ref.id, data)

        # 获取 Artifact 引用
        fetched_ref = await registry.get(ref.id)

        assert fetched_ref is not None
        assert fetched_ref.id == ref.id
        assert fetched_ref.metadata.name == "test_file.txt"
        assert fetched_ref.storage_path is not None

        await db.rollback()


@pytest.mark.asyncio
async def test_increment_decrement_ref(setup_database):
    """测试引用计数"""
    async with get_db_context() as db:
        # 创建项目
        project = Project(
            name="Test Project",
            status="pending",
        )
        db.add(project)
        await db.flush()

        # 创建 Artifact Registry
        storage = LocalStorage(base_path="/tmp/test_artifacts")
        registry = ArtifactRegistry(db, storage)

        # 创建 Artifact
        metadata = ArtifactMetadata(
            name="test_file.txt",
            type=ArtifactType.METADATA,
            project_id=project.id,
            module_id="M01",
        )

        ref = await registry.create(metadata)

        # 增加引用
        await registry.increment_ref(ref.id)
        await registry.increment_ref(ref.id)

        result = await db.execute(
            select(Artifact).where(Artifact.id == ref.id)
        )
        artifact = result.scalar_one()
        assert artifact.ref_count == 2

        # 减少引用
        await registry.decrement_ref(ref.id)

        result = await db.execute(
            select(Artifact).where(Artifact.id == ref.id)
        )
        artifact = result.scalar_one()
        assert artifact.ref_count == 1

        await db.rollback()


@pytest.mark.asyncio
async def test_list_by_project(setup_database):
    """测试列出项目的所有 Artifact"""
    async with get_db_context() as db:
        # 创建项目
        project = Project(
            name="Test Project",
            status="pending",
        )
        db.add(project)
        await db.flush()

        # 创建 Artifact Registry
        storage = LocalStorage(base_path="/tmp/test_artifacts")
        registry = ArtifactRegistry(db, storage)

        # 创建多个 Artifact
        for i in range(3):
            metadata = ArtifactMetadata(
                name=f"test_file_{i}.txt",
                type=ArtifactType.METADATA,
                project_id=project.id,
                module_id="M01",
            )
            ref = await registry.create(metadata)
            data = io.BytesIO(f"Content {i}".encode())
            await registry.upload(ref.id, data)

        # 列出所有 Artifact
        artifacts = await registry.list_by_project(project.id)

        assert len(artifacts) == 3
        assert all(a.metadata.project_id == project.id for a in artifacts)

        await db.rollback()


@pytest.mark.asyncio
async def test_list_by_project_with_type_filter(setup_database):
    """测试按类型过滤 Artifact"""
    async with get_db_context() as db:
        # 创建项目
        project = Project(
            name="Test Project",
            status="pending",
        )
        db.add(project)
        await db.flush()

        # 创建 Artifact Registry
        storage = LocalStorage(base_path="/tmp/test_artifacts")
        registry = ArtifactRegistry(db, storage)

        # 创建不同类型的 Artifact
        metadata1 = ArtifactMetadata(
            name="video.mp4",
            type=ArtifactType.VIDEO,
            project_id=project.id,
            module_id="M01",
        )
        ref1 = await registry.create(metadata1)
        data1 = io.BytesIO(b"video data")
        await registry.upload(ref1.id, data1)

        metadata2 = ArtifactMetadata(
            name="audio.wav",
            type=ArtifactType.AUDIO,
            project_id=project.id,
            module_id="M05",
        )
        ref2 = await registry.create(metadata2)
        data2 = io.BytesIO(b"audio data")
        await registry.upload(ref2.id, data2)

        # 按类型过滤
        video_artifacts = await registry.list_by_project(project.id, ArtifactType.VIDEO)
        audio_artifacts = await registry.list_by_project(project.id, ArtifactType.AUDIO)

        assert len(video_artifacts) == 1
        assert len(audio_artifacts) == 1
        assert video_artifacts[0].metadata.type == ArtifactType.VIDEO
        assert audio_artifacts[0].metadata.type == ArtifactType.AUDIO

        await db.rollback()


@pytest.mark.asyncio
async def test_delete_artifact(setup_database):
    """测试删除 Artifact（软删除）"""
    async with get_db_context() as db:
        # 创建项目
        project = Project(
            name="Test Project",
            status="pending",
        )
        db.add(project)
        await db.flush()

        # 创建 Artifact Registry
        storage = LocalStorage(base_path="/tmp/test_artifacts")
        registry = ArtifactRegistry(db, storage)

        # 创建 Artifact
        metadata = ArtifactMetadata(
            name="test_file.txt",
            type=ArtifactType.METADATA,
            project_id=project.id,
            module_id="M01",
        )

        ref = await registry.create(metadata)
        data = io.BytesIO(b"Hello, World!")
        await registry.upload(ref.id, data)

        # 删除 Artifact
        await registry.delete(ref.id)

        # 检查状态
        result = await db.execute(
            select(Artifact).where(Artifact.id == ref.id)
        )
        artifact = result.scalar_one()
        assert artifact.status == ArtifactStatus.ARCHIVED

        await db.rollback()


def test_checksum_calculation():
    """测试校验和计算"""
    # 测试不同数据
    data1 = io.BytesIO(b"Hello, World!")
    checksum1 = calculate_checksum(data1)

    data2 = io.BytesIO(b"Hello, World!")
    checksum2 = calculate_checksum(data2)

    data3 = io.BytesIO(b"Different content")
    checksum3 = calculate_checksum(data3)

    # 相同数据应该有相同校验和
    assert checksum1 == checksum2
    # 不同数据应该有不同校验和
    assert checksum1 != checksum3

    # 校验和应该是 SHA256 格式（64 个十六进制字符）
    assert len(checksum1) == 64
    assert all(c in "0123456789abcdef" for c in checksum1)
