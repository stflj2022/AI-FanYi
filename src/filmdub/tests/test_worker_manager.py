"""
Worker 管理器测试（Ticket 004）

覆盖 Worker 注册、心跳、状态跟踪、指令下发和超时检测。
"""
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from filmdub.orchestrator.database import AsyncSessionLocal, engine, Base
from filmdub.orchestrator.models import (
    Worker,
    WorkerStatus,
    WorkerType,
    Job,
    JobStatus,
    Project,
    ProjectStatus,
)
from filmdub.orchestrator.worker_manager import WorkerManager
from filmdub.orchestrator.jwt_handler import JWTHandler


@pytest.fixture
async def manager(db):
    """创建带独立 JWT 处理器的 WorkerManager。"""
    return WorkerManager(
        db,
        heartbeat_timeout=60,
        heartbeat_interval=10,
        jwt_handler=JWTHandler(secret_key="test-secret"),
    )


async def _seed_project(db) -> uuid.UUID:
    """创建一个项目并返回其 ID。"""
    project = Project(
        name="test-project",
        target_language="zh-CN",
        status=ProjectStatus.PROCESSING,
    )
    db.add(project)
    await db.commit()
    return project.id


@pytest.mark.asyncio
async def test_register_worker_creates_new_worker(manager):
    result = await manager.register_worker(
        name="worker-a",
        worker_type=WorkerType.CPU,
        cpu_cores=8,
        memory_gb=32,
    )

    assert "error" not in result
    assert result["name"] == "worker-a"
    assert result["status"] == WorkerStatus.STARTING.value
    assert result["cpu_cores"] == 8
    assert result["worker_token"]

    # Token 应能被 JWT 处理器验证
    handler = JWTHandler(secret_key="test-secret")
    payload = handler.verify_token(result["worker_token"])
    assert payload is not None
    assert payload["worker_id"] == result["id"]


@pytest.mark.asyncio
async def test_register_worker_duplicate_active_returns_error(manager):
    await manager.register_worker(name="worker-dup", worker_type=WorkerType.CPU)
    # 标记为活跃状态后再次注册
    result = await manager.db.execute(
        select(Worker).where(Worker.name == "worker-dup")
    )
    worker = result.scalar_one()
    worker.status = WorkerStatus.IDLE
    await manager.db.commit()

    dup = await manager.register_worker(name="worker-dup", worker_type=WorkerType.CPU)
    assert "error" in dup
    assert dup["error"] == "WORKER_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_register_worker_reactivates_offline(manager):
    await manager.register_worker(name="worker-re", worker_type=WorkerType.CPU)

    result = await manager.db.execute(
        select(Worker).where(Worker.name == "worker-re")
    )
    worker = result.scalar_one()
    worker.status = WorkerStatus.OFFLINE
    await manager.db.commit()

    reactivated = await manager.register_worker(
        name="worker-re", worker_type=WorkerType.CPU, host="10.0.0.1", port=9000
    )
    assert "error" not in reactivated
    assert reactivated["status"] == WorkerStatus.STARTING.value
    assert reactivated["host"] == "10.0.0.1"
    assert reactivated["worker_token"]


@pytest.mark.asyncio
async def test_handle_heartbeat_updates_state(manager):
    result = await manager.register_worker(name="worker-hb", worker_type=WorkerType.CPU)
    worker_id = uuid.UUID(result["id"])

    hb = await manager.handle_heartbeat(
        worker_id,
        status="busy",
        current_job_id=None,
        statistics={"jobs_completed": 5, "jobs_failed": 1, "total_runtime_seconds": 1000},
    )
    assert hb["success"] is True
    assert hb["pending_commands"] == []

    fetched = await manager.get_worker(worker_id)
    assert fetched["status"] == WorkerStatus.BUSY.value
    assert fetched["jobs_completed"] == 5
    assert fetched["jobs_failed"] == 1
    assert fetched["total_runtime_seconds"] == 1000


@pytest.mark.asyncio
async def test_handle_heartbeat_unknown_worker(manager):
    hb = await manager.handle_heartbeat(uuid.uuid4(), status="idle")
    assert hb["error"] == "WORKER_NOT_FOUND"


@pytest.mark.asyncio
async def test_list_and_get_worker(manager):
    await manager.register_worker(name="worker-1", worker_type=WorkerType.CPU)
    await manager.register_worker(
        name="worker-2", worker_type=WorkerType.GPU, gpu_count=2
    )

    workers = await manager.list_workers()
    assert len(workers) == 2

    gpu_workers = await manager.list_workers(worker_type=WorkerType.GPU)
    assert len(gpu_workers) == 1
    assert gpu_workers[0]["gpu_count"] == 2


@pytest.mark.asyncio
async def test_unregister_worker(manager):
    result = await manager.register_worker(name="worker-un", worker_type=WorkerType.CPU)
    worker_id = uuid.UUID(result["id"])

    ok = await manager.unregister_worker(worker_id)
    assert ok is True

    fetched = await manager.get_worker(worker_id)
    assert fetched["status"] == WorkerStatus.STOPPING.value

    assert await manager.unregister_worker(uuid.uuid4()) is False


@pytest.mark.asyncio
async def test_check_timeouts_reschedules_job(manager):
    project_id = await _seed_project(manager.db)

    # 直接创建一个 BUSY 且心跳过期的 Worker
    worker = Worker(
        name="worker-timeout",
        status=WorkerStatus.BUSY,
        type=WorkerType.CPU,
        last_heartbeat=datetime.utcnow() - timedelta(seconds=300),
        heartbeat_interval_seconds=10,
    )
    manager.db.add(worker)
    await manager.db.flush()

    job = Job(
        project_id=project_id,
        name="timeout-job",
        status=JobStatus.RUNNING,
        module_id="M04",
        worker_id=worker.id,
    )
    manager.db.add(job)
    await manager.db.commit()

    worker.current_job_id = job.id
    await manager.db.commit()

    await manager.check_timeouts()

    result = await manager.db.execute(
        select(Worker).where(Worker.id == worker.id)
    )
    updated_worker = result.scalar_one()
    assert updated_worker.status == WorkerStatus.OFFLINE
    assert updated_worker.current_job_id is None

    job_result = await manager.db.execute(select(Job).where(Job.id == job.id))
    updated_job = job_result.scalar_one()
    assert updated_job.status == JobStatus.PENDING
    assert updated_job.worker_id is None
