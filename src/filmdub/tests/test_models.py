"""
数据库模型测试
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

try:
    from src.filmdub.orchestrator.database import AsyncSessionLocal, get_db_context
    from src.filmdub.orchestrator.models import (
        Project,
        ProjectStatus,
        Job,
        JobStatus,
        Artifact,
        ArtifactType,
        ArtifactStatus,
        Worker,
        WorkerStatus,
        Character,
        VoiceProfile,
        ErrorLog,
    )
except ImportError:
    from filmdub.orchestrator.database import AsyncSessionLocal, get_db_context
    from filmdub.orchestrator.models import (
        Project,
        ProjectStatus,
        Job,
        JobStatus,
        Artifact,
        ArtifactType,
        ArtifactStatus,
        Worker,
        WorkerStatus,
        Character,
        VoiceProfile,
        ErrorLog,
    )


@pytest.mark.asyncio
async def test_create_project():
    """测试创建项目"""
    async with get_db_context() as db:
        project = Project(
            name="Test Project",
            description="A test project",
            status=ProjectStatus.PENDING,
            title="Test Title",
            title_en="Test Title English",
            season=1,
            episode=1,
            year=2024,
            original_language="en",
            target_language="zh-CN",
            tmdb_id=12345,
        )
        db.add(project)
        await db.flush()

        assert project.id is not None
        assert project.name == "Test Project"
        assert project.status == ProjectStatus.PENDING

        await db.rollback()


@pytest.mark.asyncio
async def test_project_job_relationship():
    """测试项目和作业的关系"""
    async with get_db_context() as db:
        # 创建项目
        project = Project(
            name="Test Project",
            status=ProjectStatus.PENDING,
        )
        db.add(project)
        await db.flush()

        # 创建作业
        job = Job(
            project_id=project.id,
            name="Test Job",
            status=JobStatus.PENDING,
            module_id="M01",
        )
        db.add(job)
        await db.flush()

        # 刷新项目以获取关系
        await db.refresh(project, ["jobs"])

        # 检查关系
        assert job.project_id == project.id
        assert len(project.jobs) == 1
        assert project.jobs[0].id == job.id

        await db.rollback()


@pytest.mark.asyncio
async def test_artifact_creation():
    """测试创建 Artifact"""
    async with get_db_context() as db:
        project = Project(
            name="Test Project",
            status=ProjectStatus.PENDING,
        )
        db.add(project)
        await db.flush()

        artifact = Artifact(
            name="test_video.mp4",
            type=ArtifactType.VIDEO,
            status=ArtifactStatus.READY,
            project_id=project.id,
            module_id="M01",
            storage_type="minio",
            storage_path="test/path",
            storage_bucket="test-bucket",
            size_bytes=1024000,
            mime_type="video/mp4",
            checksum="abc123",
            extra_metadata={"key": "value"},
        )
        db.add(artifact)
        await db.flush()

        assert artifact.id is not None
        assert artifact.type == ArtifactType.VIDEO
        assert artifact.status == ArtifactStatus.READY
        assert artifact.extra_metadata == {"key": "value"}

        await db.rollback()


@pytest.mark.asyncio
async def test_worker_creation():
    """测试创建 Worker"""
    async with get_db_context() as db:
        worker = Worker(
            name="test-worker-01",
            status=WorkerStatus.IDLE,
            capabilities={
                "modules": ["M01", "M02", "M09"],
                "gpu": True,
                "gpu_memory_gb": 16,
            },
            cpu_cores=8,
            memory_gb=32,
            gpu_count=1,
            gpu_memory_gb=16,
            host="localhost",
            port=8001,
        )
        db.add(worker)
        await db.flush()

        assert worker.id is not None
        assert worker.name == "test-worker-01"
        assert worker.status == WorkerStatus.IDLE
        assert worker.capabilities["modules"] == ["M01", "M02", "M09"]

        await db.rollback()


@pytest.mark.asyncio
async def test_character_creation():
    """测试创建人物"""
    async with get_db_context() as db:
        project = Project(
            name="Test Project",
            status=ProjectStatus.PENDING,
        )
        db.add(project)
        await db.flush()

        character = Character(
            project_id=project.id,
            name="Test Character",
            name_en="Test Character",
            aliases=["Alias1", "Alias2"],
            description="A test character",
        )
        db.add(character)
        await db.flush()

        assert character.id is not None
        assert character.name == "Test Character"
        assert character.aliases == ["Alias1", "Alias2"]

        await db.rollback()


@pytest.mark.asyncio
async def test_voice_profile_creation():
    """测试创建音色档案"""
    async with get_db_context() as db:
        project = Project(
            name="Test Project",
            status=ProjectStatus.PENDING,
        )
        db.add(project)
        await db.flush()

        character = Character(
            project_id=project.id,
            name="Test Character",
            name_en="Test Character",
        )
        db.add(character)
        await db.flush()

        voice_profile = VoiceProfile(
            character_id=character.id,
            project_id=project.id,
            name="VOICE-TEST-V01",
            version="v1.0",
            tts_model="cosyvoice",
            tts_config={"param": "value"},
            is_active=True,
            is_validated=False,
        )
        db.add(voice_profile)
        await db.flush()

        assert voice_profile.id is not None
        assert voice_profile.name == "VOICE-TEST-V01"
        assert voice_profile.tts_model == "cosyvoice"

        await db.rollback()


@pytest.mark.asyncio
async def test_error_log_creation():
    """测试创建错误日志"""
    async with get_db_context() as db:
        error_log = ErrorLog(
            error_id=uuid.uuid4(),
            error_code="TEST_ERROR",
            error_type="TestError",
            message="A test error occurred",
            source="test_source",
            recoverability="retryable_temporary",
            severity="error",
            context={"key": "value"},
            stack_trace="Traceback...",
        )
        db.add(error_log)
        await db.flush()

        assert error_log.id is not None
        assert error_log.error_code == "TEST_ERROR"
        assert error_log.context == {"key": "value"}

        await db.rollback()


@pytest.mark.asyncio
async def test_cascade_delete():
    """测试级联删除"""
    async with get_db_context() as db:
        # 创建项目
        project = Project(
            name="Test Project",
            status=ProjectStatus.PENDING,
        )
        db.add(project)
        await db.flush()

        # 创建作业
        job = Job(
            project_id=project.id,
            name="Test Job",
            status=JobStatus.PENDING,
        )
        db.add(job)
        await db.flush()

        job_id = job.id
        project_id = project.id

        # 删除项目
        await db.delete(project)
        await db.flush()

        # 检查作业是否也被删除
        result = await db.execute(
            select(Job).where(Job.id == job_id)
        )
        assert result.first() is None

        await db.rollback()
