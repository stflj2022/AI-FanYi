"""任务 API 测试"""
import uuid
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from filmdub.core.orchestrator_db import Base, get_db
from filmdub.core.models import Job, ProjectRecord
from filmdub.apps.web.backend.main import app
from filmdub.apps.web.backend.api.schemas.job_schemas import JobStatus, JobCreate


# 测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_jobs.db"
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
from fastapi.testclient import TestClient
client = TestClient(app)


@pytest.fixture(scope="function")
async def setup_database():
    """设置测试数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def test_user():
    """测试用户"""
    from filmdub.apps.web.backend.models import User
    return User(
        id=uuid.uuid4(),
        username="testuser",
        email="test@example.com",
        is_active=True,
    )


@pytest.fixture
def test_project():
    """测试项目"""
    return ProjectRecord(
        id=uuid.uuid4(),
        name="Test Project",
        status="pending",
    )


@pytest.fixture
def auth_headers(test_user):
    """认证头"""
    # 在实际测试中，应该创建真实的 token
    return {"Authorization": "Bearer fake-token-for-testing"}


@pytest.mark.asyncio
class TestJobService:
    """任务服务测试"""

    async def test_create_job(self, setup_database, test_user, test_project):
        """测试创建任务"""
        async with TestingSessionLocal() as db:
            db.add(test_project)
            await db.commit()

            job_data = JobCreate(
                project_id=test_project.id,
                name="Test Job",
                description="Test job description",
            )

            job = await JobService.create_job(
                db=db,
                job_data=job_data,
                owner_id=test_user.id,
            )

            assert job.id is not None
            assert job.name == "Test Job"
            assert job.description == "Test job description"
            assert job.status == "pending"

    async def test_list_jobs(self, setup_database, test_user, test_project):
        """测试获取任务列表"""
        async with TestingSessionLocal() as db:
            db.add(test_project)
            db.flush()

            # 创建多个任务
            for i in range(3):
                job = Job(
                    project_id=test_project.id,
                    name=f"Job {i}",
                    status="pending",
                )
                db.add(job)

            await db.commit()

            jobs, total = await JobService.list_jobs(
                db=db,
                owner_id=test_user.id,
                page=1,
                page_size=10,
            )

            assert total == 3
            assert len(jobs) == 3

    async def test_get_job_by_id(self, setup_database, test_user, test_project):
        """测试根据 ID 获取任务"""
        async with TestingSessionLocal() as db:
            db.add(test_project)
            db.flush()

            job = Job(
                project_id=test_project.id,
                name="Test Job",
                status="pending",
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)

            found_job = await JobService.get_job_by_id(
                db=db,
                job_id=job.id,
                owner_id=test_user.id,
            )

            assert found_job is not None
            assert found_job.id == job.id
            assert found_job.name == "Test Job"

    async def test_pause_job(self, setup_database, test_user, test_project):
        """测试暂停任务"""
        async with TestingSessionLocal() as db:
            db.add(test_project)
            db.flush()

            job = Job(
                project_id=test_project.id,
                name="Test Job",
                status="running",
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)

            paused_job = await JobService.pause_job(
                db=db,
                job_id=job.id,
                reason="Test pause",
                owner_id=test_user.id,
            )

            assert paused_job.status == "waiting"
            assert "暂停" in paused_job.error_message or "pause" in paused_job.error_message.lower()

    async def test_resume_job(self, setup_database, test_user, test_project):
        """测试恢复任务"""
        async with TestingSessionLocal() as db:
            db.add(test_project)
            db.flush()

            job = Job(
                project_id=test_project.id,
                name="Test Job",
                status="waiting",
                error_message="Paused",
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)

            resumed_job = await JobService.resume_job(
                db=db,
                job_id=job.id,
                owner_id=test_user.id,
            )

            assert resumed_job.status == "scheduled"
            assert resumed_job.scheduled_at is not None
            assert resumed_job.error_message is None

    async def test_cancel_job(self, setup_database, test_user, test_project):
        """测试取消任务"""
        async with TestingSessionLocal() as db:
            db.add(test_project)
            db.flush()

            job = Job(
                project_id=test_project.id,
                name="Test Job",
                status="scheduled",
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)

            cancelled_job = await JobService.cancel_job(
                db=db,
                job_id=job.id,
                reason="Test cancel",
                owner_id=test_user.id,
            )

            assert cancelled_job.status == "cancelled"
            assert cancelled_job.completed_at is not None

    async def test_retry_job(self, setup_database, test_user, test_project):
        """测试重试任务"""
        async with TestingSessionLocal() as db:
            db.add(test_project)
            db.flush()

            job = Job(
                project_id=test_project.id,
                name="Test Job",
                status="failed",
                error_message="Test error",
                retry_count=0,
                max_retries=3,
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)

            retried_job = await JobService.retry_job(
                db=db,
                job_id=job.id,
                owner_id=test_user.id,
            )

            assert retried_job.status == "scheduled"
            assert retried_job.retry_count == 1
            assert retried_job.error_message is None


class TestJobStatusTransitions:
    """任务状态转换测试"""

    @pytest.mark.parametrize(
        "initial_status,action,expected_status",
        [
            ("scheduled", "pause", "waiting"),
            ("running", "pause", "waiting"),
            ("retrying", "pause", "waiting"),
            ("waiting", "resume", "scheduled"),
            ("pending", "cancel", "cancelled"),
            ("scheduled", "cancel", "cancelled"),
            ("running", "cancel", "cancelled"),
            ("failed", "retry", "scheduled"),
        ],
    )
    async def test_status_transitions(
        self,
        setup_database,
        test_user,
        test_project,
        initial_status,
        action,
        expected_status,
    ):
        """测试状态转换"""
        async with TestingSessionLocal() as db:
            db.add(test_project)
            db.flush()

            job = Job(
                project_id=test_project.id,
                name="Test Job",
                status=initial_status,
            )
            if initial_status == "failed":
                job.error_message = "Test error"
                job.retry_count = 0
                job.max_retries = 3
            db.add(job)
            await db.commit()
            await db.refresh(job)

            if action == "pause":
                result = await JobService.pause_job(db, job.id, owner_id=test_user.id)
            elif action == "resume":
                result = await JobService.resume_job(db, job.id, owner_id=test_user.id)
            elif action == "cancel":
                result = await JobService.cancel_job(db, job.id, owner_id=test_user.id)
            elif action == "retry":
                result = await JobService.retry_job(db, job.id, owner_id=test_user.id)
            else:
                raise ValueError(f"Unknown action: {action}")

            assert result.status == expected_status
