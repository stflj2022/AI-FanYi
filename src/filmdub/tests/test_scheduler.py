"""
Ticket 005 调度器核心测试

覆盖依赖解析（就绪判定、循环依赖检测）、资源匹配（GPU 过滤、打分排序）、
分发引擎（状态迁移、Token 生成）与调度循环（start/stop/单周期分发）。
"""
import uuid
from datetime import datetime, timedelta

import pytest

from filmdub.orchestrator.database import get_db_context, Base, engine
from filmdub.orchestrator.models import (
    Job,
    JobStatus,
    Project,
    ProjectStatus,
    Worker,
    WorkerStatus,
    WorkerType,
)
from filmdub.orchestrator.scheduler import (
    DependencyResolver,
    ResourceMatcher,
    DispatchEngine,
    Scheduler,
)
from filmdub.orchestrator.jwt_handler import JWTHandler

async def _seed_project(db, status=ProjectStatus.PROCESSING):
    project = Project(
        name=f"proj-{uuid.uuid4().hex[:8]}",
        status=status,
        target_language="zh-CN",
    )
    db.add(project)
    await db.flush()
    return project


async def _seed_worker(
    db,
    name=None,
    worker_type=WorkerType.CPU,
    cpu_cores=8,
    memory_gb=32,
    gpu_count=0,
    gpu_memory_gb=0,
    status=WorkerStatus.IDLE,
    current_job_id=None,
):
    worker = Worker(
        name=name or f"worker-{uuid.uuid4().hex[:6]}",
        status=status,
        type=worker_type,
        capabilities={"modules": ["M01", "M05", "M06"]},
        cpu_cores=cpu_cores,
        memory_gb=memory_gb,
        gpu_count=gpu_count,
        gpu_memory_gb=gpu_memory_gb,
        jobs_completed=0,
        jobs_failed=0,
        total_runtime_seconds=0,
        heartbeat_interval_seconds=10,
        host="localhost",
        port=8001,
        current_job_id=current_job_id,
    )
    db.add(worker)
    await db.flush()
    return worker


# ==================== 依赖解析 ====================


@pytest.mark.asyncio
async def test_resolve_dependencies_ready_jobs(db):
    """无依赖的 PENDING 作业就绪；依赖未完成的作业不就绪。"""
    async with get_db_context() as db:
        project = await _seed_project(db)
        # 无依赖 → 就绪
        job_a = Job(
            project_id=project.id,
            name="A",
            module_id="M01",
            status=JobStatus.PENDING,
            depends_on=[],
        )
        db.add(job_a)
        await db.flush()
        # 依赖未完成 → 不就绪
        job_b = Job(
            project_id=project.id,
            name="B",
            module_id="M02",
            status=JobStatus.PENDING,
            depends_on=[str(job_a.id)],
        )
        db.add(job_b)
        await db.flush()

        resolver = DependencyResolver(db)
        ready = await resolver.get_ready_jobs(project.id)
        assert [j.id for j in ready] == [job_a.id]

        # 完成 job_a 后 job_b 就绪
        job_a.status = JobStatus.COMPLETED
        await db.flush()
        ready2 = await resolver.get_ready_jobs(project.id)
        assert job_b.id in [j.id for j in ready2]


@pytest.mark.asyncio
async def test_resolve_dependencies_status_gate(db):
    """RUNNING / COMPLETED 状态的作业不会重复进入就绪队列。"""
    async with get_db_context() as db:
        project = await _seed_project(db)
        running = Job(
            project_id=project.id,
            name="running",
            module_id="M01",
            status=JobStatus.RUNNING,
            depends_on=[],
        )
        completed = Job(
            project_id=project.id,
            name="done",
            module_id="M02",
            status=JobStatus.COMPLETED,
            depends_on=[],
        )
        db.add_all([running, completed])
        await db.flush()

        resolver = DependencyResolver(db)
        ready = await resolver.get_ready_jobs(project.id)
        assert ready == []


@pytest.mark.asyncio
async def test_circular_dependency_detected(db):
    """循环依赖能够被检测出来。"""
    async with get_db_context() as db:
        project = await _seed_project(db)
        j1 = Job(
            project_id=project.id,
            name="j1",
            module_id="M01",
            status=JobStatus.PENDING,
            depends_on=[],
        )
        db.add(j1)
        await db.flush()
        j2 = Job(
            project_id=project.id,
            name="j2",
            module_id="M02",
            status=JobStatus.PENDING,
            depends_on=[str(j1.id)],
        )
        db.add(j2)
        await db.flush()
        # 形成环：j1 → j2 → j1
        j1.depends_on = [str(j2.id)]
        await db.flush()

        resolver = DependencyResolver(db)
        cycle = await resolver.check_circular_dependency(project.id)
        assert cycle is not None
        assert len(cycle) >= 2
        assert cycle[0] == cycle[-1] or len(set(cycle)) < len(cycle)


@pytest.mark.asyncio
async def test_no_circular_dependency(db):
    """无环依赖返回 None。"""
    async with get_db_context() as db:
        project = await _seed_project(db)
        j1 = Job(
            project_id=project.id,
            name="j1",
            module_id="M01",
            status=JobStatus.PENDING,
            depends_on=[],
        )
        j2 = Job(
            project_id=project.id,
            name="j2",
            module_id="M02",
            status=JobStatus.PENDING,
            depends_on=[str(j1.id)],
        )
        db.add_all([j1, j2])
        await db.flush()

        resolver = DependencyResolver(db)
        assert await resolver.check_circular_dependency(project.id) is None


# ==================== 资源匹配 ====================


@pytest.mark.asyncio
async def test_find_best_worker_gpu_filter(db):
    """GPU 作业只匹配 GPU Worker；CPU 作业不匹配 GPU Worker。"""
    async with get_db_context() as db:
        project = await _seed_project(db)
        gpu_worker = await _seed_worker(
            db,
            worker_type=WorkerType.GPU,
            gpu_count=1,
            gpu_memory_gb=16,
            cpu_cores=4,
            memory_gb=16,
        )
        cpu_worker = await _seed_worker(
            db,
            worker_type=WorkerType.CPU,
            cpu_cores=8,
            memory_gb=32,
        )
        job = Job(
            project_id=project.id,
            name="gpu-job",
            module_id="M09",
            status=JobStatus.PENDING,
        )
        db.add(job)
        await db.flush()

        matcher = ResourceMatcher(db)
        # GPU 作业 → 只可能命中 GPU worker
        best_gpu = await matcher.find_best_worker(job, require_gpu=True)
        assert best_gpu is not None
        assert best_gpu.id == gpu_worker.id

        # CPU 作业 → GPU worker 被排除
        cpu_job = Job(
            project_id=project.id,
            name="cpu-job",
            module_id="M01",
            status=JobStatus.PENDING,
        )
        db.add(cpu_job)
        await db.flush()
        best_cpu = await matcher.find_best_worker(cpu_job, require_gpu=False)
        assert best_cpu is not None
        assert best_cpu.id == cpu_worker.id


@pytest.mark.asyncio
async def test_find_best_worker_busy_excluded(db):
    """BUSY Worker 不会被选中。"""
    async with get_db_context() as db:
        project = await _seed_project(db)
        busy = await _seed_worker(
            db,
            worker_type=WorkerType.CPU,
            status=WorkerStatus.BUSY,
            current_job_id=uuid.uuid4(),
        )
        job = Job(
            project_id=project.id,
            name="job",
            module_id="M01",
            status=JobStatus.PENDING,
        )
        db.add(job)
        await db.flush()

        matcher = ResourceMatcher(db)
        best = await matcher.find_best_worker(job, require_gpu=False)
        assert best is None or best.id != busy.id


@pytest.mark.asyncio
async def test_score_worker_prefers_module_match(db):
    """能力匹配的 Worker 分数更高，被优先选择。"""
    async with get_db_context() as db:
        project = await _seed_project(db)
        w_match = await _seed_worker(db, name="match-worker")
        # 无能力匹配的 Worker
        w_no_match = Worker(
            name="nomatch-worker",
            status=WorkerStatus.IDLE,
            type=WorkerType.CPU,
            capabilities={"modules": ["M99"]},
            cpu_cores=8,
            memory_gb=32,
            gpu_count=0,
            gpu_memory_gb=0,
            jobs_completed=0,
            jobs_failed=0,
            total_runtime_seconds=0,
            heartbeat_interval_seconds=10,
            host="localhost",
            port=8002,
        )
        db.add(w_no_match)
        await db.flush()

        job = Job(
            project_id=project.id,
            name="M01-job",
            module_id="M01",
            status=JobStatus.PENDING,
        )
        db.add(job)
        await db.flush()

        matcher = ResourceMatcher(db)
        score_match = await matcher._score_worker_job_match(w_match, job)
        score_no = await matcher._score_worker_job_match(w_no_match, job)
        assert score_match > score_no

        best = await matcher.find_best_worker(job, require_gpu=False)
        assert best.id == w_match.id


@pytest.mark.asyncio
async def test_check_resource_sufficient(db):
    """资源不足时返回 False。"""
    async with get_db_context() as db:
        worker = await _seed_worker(
            db,
            cpu_cores=2,
            memory_gb=4,
            gpu_count=0,
        )
        matcher = ResourceMatcher(db)
        assert await matcher.check_resource_sufficient(worker, required_cpu=1, required_memory=2) is True
        assert await matcher.check_resource_sufficient(worker, required_cpu=8) is False
        assert await matcher.check_resource_sufficient(worker, require_gpu=True) is False


# ==================== 分发引擎 ====================


@pytest.mark.asyncio
async def test_dispatch_job_updates_state(db):
    """分发后作业 SCHEDULED、Worker BUSY、返回 Token。"""
    async with get_db_context() as db:
        project = await _seed_project(db)
        worker = await _seed_worker(db)
        job = Job(
            project_id=project.id,
            name="dispatch-me",
            module_id="M01",
            status=JobStatus.PENDING,
        )
        db.add(job)
        await db.flush()

        engine = DispatchEngine(db, JWTHandler())
        info = await engine.dispatch_job(job, worker)
        await db.flush()

        assert job.status == JobStatus.SCHEDULED
        assert job.worker_id == worker.id
        assert job.scheduled_at is not None
        assert worker.status == WorkerStatus.BUSY
        assert worker.current_job_id == job.id
        assert info["job_id"] == str(job.id)
        assert info["module_id"] == "M01"
        # Token 真实可验证
        jwt = JWTHandler()
        payload = jwt.verify_token(info["worker_token"])
        assert payload is not None
        assert payload["worker_id"] == str(worker.id)


# ==================== 调度循环 ====================


@pytest.mark.asyncio
async def test_scheduler_single_cycle_dispatches(db):
    """一次调度周期内，就绪作业被分发到可用 Worker。"""
    async with get_db_context() as db:
        project = await _seed_project(db)
        await _seed_worker(db)
        job = Job(
            project_id=project.id,
            name="cycle-job",
            module_id="M01",
            status=JobStatus.PENDING,
            depends_on=[],
        )
        db.add(job)
        await db.flush()

        scheduler = Scheduler(db, JWTHandler(), cycle_interval=0.01)
        await scheduler._schedule_cycle()

        await db.refresh(job)
        assert job.status == JobStatus.SCHEDULED


@pytest.mark.asyncio
async def test_scheduler_start_stop(db):
    """start/stop 生命周期：重复 start 不报错，stop 后循环终止。"""
    async with get_db_context() as db:
        scheduler = Scheduler(db, JWTHandler(), cycle_interval=0.01)
        await scheduler.start()
        await scheduler.start()  # 重复启动被忽略
        assert scheduler._running is True
        await scheduler.stop()
        assert scheduler._running is False
        await scheduler.stop()  # 重复停止安全


@pytest.mark.asyncio
async def test_scheduler_skips_non_processing_projects(db):
    """非 PROCESSING 状态的项目不被调度。"""
    async with get_db_context() as db:
        project = await _seed_project(db, status=ProjectStatus.PENDING)
        await _seed_worker(db)
        job = Job(
            project_id=project.id,
            name="should-not-run",
            module_id="M01",
            status=JobStatus.PENDING,
            depends_on=[],
        )
        db.add(job)
        await db.flush()

        scheduler = Scheduler(db, JWTHandler(), cycle_interval=0.01)
        await scheduler._schedule_cycle()

        await db.refresh(job)
        assert job.status == JobStatus.PENDING
