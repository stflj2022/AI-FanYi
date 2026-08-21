"""
Ticket 003 REST API 测试

覆盖项目和作业的 CRUD 与生命周期管理端点：
- 项目：创建、列表、详情、更新、删除、统计、启动、取消
- 作业：创建、列表、详情、取消、重试、删除、日志
"""
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from filmdub.orchestrator.database import get_db, AsyncSessionLocal, engine, Base
from filmdub.orchestrator.models import Project, ProjectStatus, Job, JobStatus, Worker, WorkerStatus
from filmdub.apps.api.main import app


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def setup_db():
    """初始化测试数据库。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="module")
async def client(setup_db):
    """提供带依赖覆盖的 HTTP 客户端。"""
    async def _override_get_db():
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _create_project(client, name="API Test Project"):
    resp = await client.post(
        "/api/v1/projects",
        json={"name": name, "title": "Test Title", "target_language": "zh-CN"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ==================== 项目 CRUD ====================


async def test_create_project(client):
    data = await _create_project(client, "Create Test")
    assert data["name"] == "Create Test"
    assert data["status"] == ProjectStatus.PENDING.value
    assert "id" in data


async def test_create_project_duplicate_tmdb(client):
    await _create_project(client, "Tmdb Dup")
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Tmdb Dup 2", "tmdb_id": 99999},
    )
    assert resp.status_code == 201
    # 再次使用相同 tmdb_id 应冲突
    resp2 = await client.post(
        "/api/v1/projects",
        json={"name": "Tmdb Dup 3", "tmdb_id": 99999},
    )
    assert resp2.status_code == 409


async def test_list_projects(client):
    await _create_project(client, "List A")
    await _create_project(client, "List B")
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


async def test_list_projects_invalid_status(client):
    resp = await client.get("/api/v1/projects", params={"status": "not-a-status"})
    assert resp.status_code == 400


async def test_get_project(client):
    created = await _create_project(client, "Get Test")
    resp = await client.get(f"/api/v1/projects/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Get Test"


async def test_get_project_not_found(client):
    resp = await client.get(f"/api/v1/projects/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_update_project(client):
    created = await _create_project(client, "Update Test")
    resp = await client.patch(
        f"/api/v1/projects/{created['id']}",
        json={"description": "Updated description"},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated description"


async def test_update_project_invalid_status(client):
    created = await _create_project(client, "Update Bad Status")
    resp = await client.patch(
        f"/api/v1/projects/{created['id']}",
        json={"status": "bogus"},
    )
    assert resp.status_code == 400


async def test_delete_project(client):
    created = await _create_project(client, "Delete Test")
    resp = await client.delete(f"/api/v1/projects/{created['id']}")
    assert resp.status_code == 204
    # 再次获取应为 404
    resp2 = await client.get(f"/api/v1/projects/{created['id']}")
    assert resp2.status_code == 404


async def test_project_statistics(client):
    created = await _create_project(client, "Stats Test")
    # 创建两个作业
    for i in range(2):
        resp = await client.post(
            f"/api/v1/jobs/projects/{created['id']}",
            json={"name": f"job-{i}", "module_id": "M01"},
        )
        assert resp.status_code == 201

    resp = await client.get(f"/api/v1/projects/{created['id']}/statistics")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_jobs"] == 2
    assert stats["pending_jobs"] == 2


# ==================== 项目生命周期 ====================


async def test_start_project(client):
    created = await _create_project(client, "Start Test")
    resp = await client.post(f"/api/v1/projects/{created['id']}/start")
    assert resp.status_code == 202
    assert resp.json()["status"] == ProjectStatus.PROCESSING.value


async def test_start_project_twice_conflict(client):
    created = await _create_project(client, "Start Twice")
    await client.post(f"/api/v1/projects/{created['id']}/start")
    resp = await client.post(f"/api/v1/projects/{created['id']}/start")
    assert resp.status_code == 409


async def test_cancel_project_cancels_jobs(client):
    created = await _create_project(client, "Cancel Test")
    job_resp = await client.post(
        f"/api/v1/jobs/projects/{created['id']}",
        json={"name": "cancellable-job", "module_id": "M01"},
    )
    job_id = job_resp.json()["id"]

    resp = await client.post(f"/api/v1/projects/{created['id']}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == ProjectStatus.CANCELLED.value
    assert resp.json()["cancelled_jobs"] >= 1

    # 作业应被取消
    job_get = await client.get(f"/api/v1/jobs/{job_id}")
    assert job_get.json()["status"] == JobStatus.CANCELLED.value


# ==================== 作业 CRUD 与生命周期 ====================


async def test_create_job(client):
    project = await _create_project(client, "Job Create Project")
    resp = await client.post(
        f"/api/v1/jobs/projects/{project['id']}",
        json={"name": "job-1", "module_id": "M01"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["module_id"] == "M01"
    assert data["status"] == JobStatus.PENDING.value


async def test_create_job_project_not_found(client):
    resp = await client.post(
        f"/api/v1/jobs/projects/{uuid.uuid4()}",
        json={"name": "orphan-job", "module_id": "M01"},
    )
    assert resp.status_code == 404


async def test_create_job_missing_dependency(client):
    project = await _create_project(client, "Dep Project")
    missing_dep = uuid.uuid4()
    resp = await client.post(
        f"/api/v1/jobs/projects/{project['id']}",
        json={"name": "dep-job", "module_id": "M01", "depends_on": [str(missing_dep)]},
    )
    assert resp.status_code == 404


async def test_list_project_jobs(client):
    project = await _create_project(client, "List Jobs Project")
    await client.post(
        f"/api/v1/jobs/projects/{project['id']}",
        json={"name": "j-a", "module_id": "M01"},
    )
    await client.post(
        f"/api/v1/jobs/projects/{project['id']}",
        json={"name": "j-b", "module_id": "M02"},
    )
    resp = await client.get(f"/api/v1/jobs/projects/{project['id']}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp_filtered = await client.get(
        f"/api/v1/jobs/projects/{project['id']}",
        params={"module": "M02"},
    )
    assert len(resp_filtered.json()) == 1


async def test_get_job(client):
    project = await _create_project(client, "Get Job Project")
    created = await client.post(
        f"/api/v1/jobs/projects/{project['id']}",
        json={"name": "get-me", "module_id": "M01"},
    )
    job_id = created.json()["id"]
    resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "get-me"


async def test_get_job_not_found(client):
    resp = await client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_cancel_job(client):
    project = await _create_project(client, "Cancel Job Project")
    created = await client.post(
        f"/api/v1/jobs/projects/{project['id']}",
        json={"name": "cancel-me", "module_id": "M01"},
    )
    job_id = created.json()["id"]

    resp = await client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == JobStatus.CANCELLED.value


async def test_cancel_job_releases_worker(client):
    project = await _create_project(client, "Cancel Worker Project")
    job_resp = await client.post(
        f"/api/v1/jobs/projects/{project['id']}",
        json={"name": "worker-job", "module_id": "M01"},
    )
    job_id = job_resp.json()["id"]

    # 手动将一个 Worker 绑定到该作业（模拟运行中）
    async with AsyncSessionLocal() as session:
        worker = Worker(
            name="test-worker-1",
            status=WorkerStatus.BUSY,
            current_job_id=uuid.UUID(job_id),
            cpu_cores=4,
            memory_gb=16,
        )
        session.add(worker)
        await session.flush()
        worker_id = worker.id
        job_obj = (await session.execute(select(Job).where(Job.id == uuid.UUID(job_id)))).scalar_one()
        job_obj.worker_id = worker.id
        job_obj.status = JobStatus.RUNNING
        await session.commit()

    resp = await client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert resp.status_code == 200

    async with AsyncSessionLocal() as session:
        worker_obj = await session.get(Worker, worker_id)
        assert worker_obj.status == WorkerStatus.IDLE
        assert worker_obj.current_job_id is None


async def test_retry_job(client):
    project = await _create_project(client, "Retry Project")
    created = await client.post(
        f"/api/v1/jobs/projects/{project['id']}",
        json={"name": "retry-me", "module_id": "M01"},
    )
    job_id = created.json()["id"]

    # 手动将作业标记为失败
    async with AsyncSessionLocal() as session:
        job_obj = (await session.execute(select(Job).where(Job.id == uuid.UUID(job_id)))).scalar_one()
        job_obj.status = JobStatus.FAILED
        job_obj.error_message = "boom"
        await session.commit()

    resp = await client.post(f"/api/v1/jobs/{job_id}/retry")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == JobStatus.PENDING.value
    assert data["retry_count"] == 1
    assert data["error_message"] is None


async def test_retry_job_only_failed(client):
    project = await _create_project(client, "Retry Only Failed")
    created = await client.post(
        f"/api/v1/jobs/projects/{project['id']}",
        json={"name": "not-failed", "module_id": "M01"},
    )
    job_id = created.json()["id"]
    resp = await client.post(f"/api/v1/jobs/{job_id}/retry")
    assert resp.status_code == 400


async def test_retry_job_max_retries(client):
    project = await _create_project(client, "Retry Max")
    created = await client.post(
        f"/api/v1/jobs/projects/{project['id']}",
        json={"name": "max-out", "module_id": "M01"},
    )
    job_id = created.json()["id"]

    async with AsyncSessionLocal() as session:
        job_obj = (await session.execute(select(Job).where(Job.id == uuid.UUID(job_id)))).scalar_one()
        job_obj.status = JobStatus.FAILED
        job_obj.retry_count = job_obj.max_retries
        await session.commit()

    resp = await client.post(f"/api/v1/jobs/{job_id}/retry")
    assert resp.status_code == 400


async def test_delete_job(client):
    project = await _create_project(client, "Delete Job Project")
    created = await client.post(
        f"/api/v1/jobs/projects/{project['id']}",
        json={"name": "delete-me", "module_id": "M01"},
    )
    job_id = created.json()["id"]

    resp = await client.delete(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 204
    resp2 = await client.get(f"/api/v1/jobs/{job_id}")
    assert resp2.status_code == 404


async def test_delete_running_job_conflict(client):
    project = await _create_project(client, "Delete Running")
    created = await client.post(
        f"/api/v1/jobs/projects/{project['id']}",
        json={"name": "running-job", "module_id": "M01"},
    )
    job_id = created.json()["id"]

    async with AsyncSessionLocal() as session:
        job_obj = (await session.execute(select(Job).where(Job.id == uuid.UUID(job_id)))).scalar_one()
        job_obj.status = JobStatus.RUNNING
        await session.commit()

    resp = await client.delete(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 409


async def test_get_job_logs(client):
    project = await _create_project(client, "Logs Project")
    created = await client.post(
        f"/api/v1/jobs/projects/{project['id']}",
        json={"name": "log-job", "module_id": "M01"},
    )
    job_id = created.json()["id"]

    resp = await client.get(f"/api/v1/jobs/{job_id}/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == job_id
    assert "logs" in data
    # 创建作业时应已写入日志
    assert any(e["event"] == "created" for e in data["logs"])


async def test_get_job_logs_not_found(client):
    resp = await client.get(f"/api/v1/jobs/{uuid.uuid4()}/logs")
    assert resp.status_code == 404
