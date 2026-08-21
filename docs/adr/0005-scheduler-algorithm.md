# ADR 0005: 调度器算法设计

## 状态

设计中

## 上下文

Layer 0 调度器负责将 Job 分配给合适的 Worker，管理执行顺序，处理依赖关系。需要设计一个高效、可靠的调度算法。

## 核心需求

1. **依赖管理**: 确保 Job 按正确顺序执行（DAG）
2. **资源匹配**: 根据 Job 类型分配合适的 Worker
3. **负载均衡**: 避免某些 Worker 过载
4. **容错处理**: Worker 故障时重新调度
5. **优先级**: 支持作业优先级
6. **断点恢复**: 系统崩溃后能恢复执行

## 调度器架构

```
┌─────────────────────────────────────────────────────────┐
│                    Scheduler                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐               │
│  │ Job Queue    │──────│ Dependency   │               │
│  │ (Priority)   │      | Resolver     │               │
│  └──────────────┘      └──────────────┘               │
│         │                         │                     │
│         ▼                         ▼                     │
│  ┌──────────────┐      ┌──────────────┐               │
│  │ Resource     │──────│ Assignment   │               │
│  │ Matcher      │      │ Engine       │               │
│  └──────────────┘      └──────────────┘               │
│                                │                         │
│                                ▼                         │
│                        ┌──────────────┐                │
│                        │ Dispatcher   │                │
│                        └──────────────┘                │
└─────────────────────────────────────────────────────────┘
```

## 数据结构

### Job 调度状态

```python
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class SchedulingStatus(Enum):
    """调度状态"""
    QUEUED = "queued"           # 在队列中等待
    READY = "ready"             # 依赖满足，可调度
    SCHEDULED = "scheduled"     # 已分配给 Worker
    DISPATCHED = "dispatched"   # 已发送给 Worker
    RUNNING = "running"         # 执行中
    WAITING = "waiting"         # 等待依赖
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消
    RETRYING = "retrying"       # 重试中

@dataclass
class JobScheduleInfo:
    """Job 调度信息"""
    job_id: uuid.UUID
    project_id: uuid.UUID
    module_id: str              # M01-M14
    status: SchedulingStatus

    # 依赖
    depends_on: List[uuid.UUID] = None        # 依赖的 Job ID
    dependents: List[uuid.UUID] = None        # 依赖此 Job 的其他 Job

    # 调度约束
    required_resources: Dict[str, Any] = None  # 资源需求
    priority: int = 5           # 1-10，10 最高
    timeout_seconds: int = 3600  # 超时时间
    retry_count: int = 0
    max_retries: int = 3

    # 时间
    created_at: datetime = None
    ready_at: datetime = None    # 依赖满足的时间
    scheduled_at: datetime = None
    dispatched_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None

    # 分配信息
    assigned_worker_id: Optional[uuid.UUID] = None
    assignment_score: Optional[float] = None  # 匹配度分数

    # 错误信息
    last_error: Optional[str] = None
    failure_reason: Optional[str] = None
```

### Worker 资源状态

```python
@dataclass
class WorkerResources:
    """Worker 资源状态"""
    worker_id: uuid.UUID
    worker_type: str            # cpu, gpu, io, hybrid

    # 资源容量
    cpu_cores: int
    memory_gb: int
    gpu_count: int
    gpu_memory_gb: int

    # 资源使用 (0.0 - 1.0)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    gpu_usage: float = 0.0

    # 能力
    supported_modules: List[str] = None  # ["M01", "M02", "M09"]
    supported_features: List[str] = None  # ["whisper", "cuda"]

    # 状态
    status: str = "idle"        # idle, busy, offline
    current_job_id: Optional[uuid.UUID] = None
    queue_size: int = 0         # 本地队列中的任务数

    # 统计
    jobs_completed: int = 0
    jobs_failed: int = 0
    total_runtime_seconds: int = 0
    average_job_time_seconds: float = 0.0
```

## 调度算法

### 1. 依赖解析器 (Dependency Resolver)

```python
class DependencyResolver:
    """DAG 依赖解析器"""

    def __init__(self, db):
        self.db = db

    async def resolve_dependencies(self, project_id: uuid.UUID) -> List[uuid.UUID]:
        """解析项目中所有 Job 的依赖，返回可执行的 Job ID 列表

        Args:
            project_id: 项目 ID

        Returns:
            可执行的 Job ID 列表
        """
        # 获取项目中所有 Job
        jobs = await self.db.fetch(
            """
            SELECT id, depends_on, status
            FROM jobs
            WHERE project_id = $1
            """,
            project_id
        )

        job_status = {job["id"]: job["status"] for job in jobs}
        job_deps = {job["id"]: job["depends_on"] or [] for job in jobs}

        ready_jobs = []

        for job_id, deps in job_deps.items():
            # 跳过已完成、失败、取消的
            if job_status[job_id] in ["completed", "failed", "cancelled"]:
                continue

            # 检查依赖是否都已完成
            if all(job_status.get(dep_id) == "completed" for dep_id in deps):
                ready_jobs.append(job_id)

        return ready_jobs

    async def get_ready_jobs(self, limit: int = 100) -> List[JobScheduleInfo]:
        """获取准备好的 Job（可用于调度）

        Args:
            limit: 最大返回数量

        Returns:
            准备好的 Job 列表，按优先级排序
        """
        # 查询所有 waiting 状态的 Job
        waiting_jobs = await self.db.fetch(
            """
            SELECT j.*, p.priority as project_priority
            FROM jobs j
            JOIN projects p ON j.project_id = p.id
            WHERE j.status = 'waiting'
            ORDER BY p.priority DESC, j.created_at ASC
            LIMIT $1
            """,
            limit
        )

        ready_jobs = []
        for job in waiting_jobs:
            # 检查依赖
            deps = job["depends_on"] or []
            deps_completed = await self._check_dependencies_completed(deps)

            if deps_completed:
                ready_jobs.append(JobScheduleInfo(
                    job_id=job["id"],
                    project_id=job["project_id"],
                    module_id=job["module_id"],
                    status=SchedulingStatus.READY,
                    depends_on=deps,
                    priority=job.get("project_priority", 5),
                    timeout_seconds=job.get("timeout_seconds", 3600),
                    max_retries=job.get("max_retries", 3),
                    created_at=job["created_at"]
                ))

        # 按优先级排序
        ready_jobs.sort(key=lambda j: (
            -j.priority,  # 优先级降序
            j.created_at   # 创建时间升序
        ))

        return ready_jobs

    async def _check_dependencies_completed(self, dep_ids: List[uuid.UUID]) -> bool:
        """检查依赖是否都已完成"""
        if not dep_ids:
            return True

        result = await self.db.fetch(
            """
            SELECT COUNT(*) as count
            FROM jobs
            WHERE id = ANY($1) AND status = 'completed'
            """,
            dep_ids
        )

        return result[0]["count"] == len(dep_ids)
```

### 2. 资源匹配器 (Resource Matcher)

```python
class ResourceMatcher:
    """资源匹配器"""

    def __init__(self, db):
        self.db = db

    async def find_best_worker(
        self,
        job: JobScheduleInfo,
        available_workers: List[WorkerResources]
    ) -> Optional[uuid.UUID]:
        """为 Job 找到最合适的 Worker

        Args:
            job: Job 调度信息
            available_workers: 可用的 Worker 列表

        Returns:
            最佳 Worker ID，如果没有合适的则返回 None
        """
        if not available_workers:
            return None

        # 过滤支持该模块的 Worker
        capable_workers = [
            w for w in available_workers
            if job.module_id in w.supported_modules
        ]

        if not capable_workers:
            return None

        # 过滤满足资源需求的 Worker
        suitable_workers = []
        for worker in capable_workers:
            if self._check_resource_sufficient(job, worker):
                suitable_workers.append(worker)

        if not suitable_workers:
            return None

        # 评分并选择最佳 Worker
        scored_workers = []
        for worker in suitable_workers:
            score = self._score_worker_job_match(worker, job)
            scored_workers.append((worker.worker_id, score))

        # 按分数排序
        scored_workers.sort(key=lambda x: x[1], reverse=True)

        return scored_workers[0][0] if scored_workers else None

    def _check_resource_sufficient(
        self,
        job: JobScheduleInfo,
        worker: WorkerResources
    ) -> bool:
        """检查 Worker 资源是否足够"""
        required = job.required_resources or {}

        # 检查 CPU
        if "cpu_cores" in required:
            available_cpu = worker.cpu_cores * (1 - worker.cpu_usage)
            if available_cpu < required["cpu_cores"]:
                return False

        # 检查内存
        if "memory_gb" in required:
            available_memory = worker.memory_gb * (1 - worker.memory_usage)
            if available_memory < required["memory_gb"]:
                return False

        # 检查 GPU
        if "gpu_count" in required:
            available_gpu = worker.gpu_count * (1 - worker.gpu_usage)
            if available_gpu < required["gpu_count"]:
                return False

        return True

    def _score_worker_job_match(
        self,
        worker: WorkerResources,
        job: JobScheduleInfo
    ) -> float:
        """为 Worker-Job 匹配打分

        考虑因素:
        1. 资源利用率 (0-30 分)
        2. Worker 负载 (0-20 分)
        3. 历史成功率 (0-20 分)
        4. 专长匹配 (0-15 分)
        5. 地理位置/网络 (0-15 分)
        """
        score = 0.0

        # 1. 资源利用率 (理想是 70-80% 利用率)
        avg_resource_usage = (
            worker.cpu_usage +
            worker.memory_usage +
            (worker.gpu_usage if worker.gpu_count > 0 else 0)
        ) / (3 if worker.gpu_count > 0 else 2)

        if 0.7 <= avg_resource_usage <= 0.8:
            resource_score = 30
        elif avg_resource_usage < 0.7:
            resource_score = 20 + (avg_resource_usage / 0.7) * 10
        else:
            resource_score = max(0, 30 - (avg_resource_usage - 0.8) * 100)

        score += resource_score

        # 2. Worker 负载 (队列大小)
        load_score = max(0, 20 - worker.queue_size * 2)
        score += load_score

        # 3. 历史成功率
        total_jobs = worker.jobs_completed + worker.jobs_failed
        if total_jobs > 0:
            success_rate = worker.jobs_completed / total_jobs
            success_score = success_rate * 20
        else:
            success_score = 10  # 新 Worker 给中等分数
        score += success_score

        # 4. 专长匹配 (Worker 是否经常处理此模块)
        # 这里可以维护一个统计，简化处理
        specialty_score = 10  # 基础分
        score += specialty_score

        # 5. 地理位置/网络 (如果有多数据中心)
        # 简化处理，给固定分数
        score += 10

        return score
```

### 3. 分发引擎 (Dispatch Engine)

```python
class DispatchEngine:
    """分发引擎"""

    def __init__(self, db, api_client):
        self.db = db
        self.api_client = api_client  # 用于调用 Worker API

    async def dispatch_job(
        self,
        job_id: uuid.UUID,
        worker_id: uuid.UUID
    ) -> bool:
        """将 Job 分发给 Worker

        Args:
            job_id: Job ID
            worker_id: Worker ID

        Returns:
            是否成功分发
        """
        # 获取 Job 信息
        job = await self.db.fetch_one(
            "SELECT * FROM jobs WHERE id = $1",
            job_id
        )
        if not job:
            return False

        # 获取 Worker 信息
        worker = await self.db.fetch_one(
            "SELECT * FROM workers WHERE id = $1",
            worker_id
        )
        if not worker:
            return False

        # 更新 Job 状态
        await self.db.execute(
            """
            UPDATE jobs
            SET status = 'dispatched',
                worker_id = $2,
                dispatched_at = NOW()
            WHERE id = $1
            """,
            job_id, worker_id
        )

        # 调用 Worker API
        try:
            # 获取输入 Artifact 信息
            input_artifacts = await self._get_input_artifacts(job["input_artifacts"])

            # 构造请求
            request = {
                "job_id": str(job_id),
                "module_id": job["module_id"],
                "config": job.get("config", {}),
                "input_artifacts": input_artifacts,
                "output_artifact_specs": job.get("output_artifact_specs", [])
            }

            # 调用 Worker
            response = await self.api_client.post(
                f"http://{worker['host']}:{worker['port']}/api/v1/jobs/accept",
                json=request,
                timeout=10
            )

            if response.status_code == 200:
                # 成功分发
                await self.db.execute(
                    """
                    UPDATE workers
                    SET current_job_id = $2, status = 'busy'
                    WHERE id = $1
                    """,
                    worker_id, job_id
                )
                return True
            else:
                # 分发失败，回滚状态
                await self.db.execute(
                    """
                    UPDATE jobs
                    SET status = 'ready', worker_id = NULL
                    WHERE id = $1
                    """,
                    job_id
                )
                return False

        except Exception as e:
            # 异常，回滚状态
            await self.db.execute(
                """
                UPDATE jobs
                SET status = 'ready', worker_id = NULL
                WHERE id = $1
                """,
                job_id
            )
            return False

    async def _get_input_artifacts(self, artifact_ids: List[uuid.UUID]) -> List[Dict]:
        """获取输入 Artifact 的下载 URL"""
        if not artifact_ids:
            return []

        artifacts = await self.db.fetch(
            """
            SELECT id, name, type, storage_path, storage_bucket
            FROM artifacts
            WHERE id = ANY($1) AND status = 'ready'
            """,
            artifact_ids
        )

        # 生成临时下载 URL
        result = []
        for artifact in artifacts:
            result.append({
                "id": str(artifact["id"]),
                "name": artifact["name"],
                "type": artifact["type"],
                "download_url": self._generate_download_url(artifact)
            })

        return result

    def _generate_download_url(self, artifact: Dict) -> str:
        """生成临时下载 URL"""
        # 使用 MinIO 预签名 URL
        # 这里简化处理
        return f"https://minio.example.com/{artifact['storage_bucket']}/{artifact['storage_path']}?expires=3600"
```

### 4. 主调度器

```python
import asyncio
from loguru import logger

class Scheduler:
    """主调度器"""

    def __init__(self, db):
        self.db = db
        self.dependency_resolver = DependencyResolver(db)
        self.resource_matcher = ResourceMatcher(db)
        self.dispatch_engine = DispatchEngine(db, None)
        self._running = False

    async def start(self):
        """启动调度器"""
        self._running = True
        logger.info("Scheduler started")

        while self._running:
            try:
                await self._schedule_cycle()
                await asyncio.sleep(1)  # 每秒一个调度周期
            except Exception as e:
                logger.error(f"Scheduler cycle error: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        """停止调度器"""
        self._running = False
        logger.info("Scheduler stopped")

    async def _schedule_cycle(self):
        """执行一个调度周期"""
        # 1. 获取准备好的 Job
        ready_jobs = await self.dependency_resolver.get_ready_jobs(limit=50)

        if not ready_jobs:
            return

        # 2. 获取可用的 Worker
        available_workers = await self._get_available_workers()

        if not available_workers:
            logger.debug("No available workers")
            return

        # 3. 为每个 Job 分配 Worker
        for job in ready_jobs:
            if not self._running:
                break

            # 找到合适的 Worker
            worker_id = await self.resource_matcher.find_best_worker(
                job,
                available_workers
            )

            if worker_id:
                # 分发 Job
                success = await self.dispatch_engine.dispatch_job(
                    job.job_id,
                    worker_id
                )

                if success:
                    # 从可用列表中移除该 Worker
                    available_workers = [
                        w for w in available_workers
                        if w.worker_id != worker_id
                    ]
                    logger.info(f"Job {job.job_id} dispatched to worker {worker_id}")
                else:
                    logger.warning(f"Failed to dispatch job {job.job_id}")
            else:
                # 没有合适的 Worker，标记为 waiting
                await self.db.execute(
                    "UPDATE jobs SET status = 'waiting' WHERE id = $1",
                    job.job_id
                )
                logger.debug(f"No suitable worker for job {job.job_id}")

    async def _get_available_workers(self) -> List[WorkerResources]:
        """获取可用的 Worker"""
        workers = await self.db.fetch(
            """
            SELECT * FROM workers
            WHERE status IN ('idle', 'busy')
            AND last_heartbeat > NOW() - INTERVAL '30 seconds'
            """
        )

        result = []
        for worker in workers:
            result.append(WorkerResources(
                worker_id=worker["id"],
                worker_type=worker["type"],
                cpu_cores=worker["cpu_cores"],
                memory_gb=worker["memory_gb"],
                gpu_count=worker.get("gpu_count", 0),
                gpu_memory_gb=worker.get("gpu_memory_gb", 0),
                cpu_usage=worker.get("cpu_usage", 0.0),
                memory_usage=worker.get("memory_usage", 0.0),
                gpu_usage=worker.get("gpu_usage", 0.0),
                supported_modules=worker.get("capabilities", {}).get("modules", []),
                status=worker["status"],
                current_job_id=worker.get("current_job_id"),
                queue_size=worker.get("queue_size", 0),
                jobs_completed=worker.get("jobs_completed", 0),
                jobs_failed=worker.get("jobs_failed", 0),
                total_runtime_seconds=worker.get("total_runtime_seconds", 0)
            ))

        return result
```

## 容错处理

### Worker 故障检测

```python
class WorkerMonitor:
    """Worker 监控"""

    async def check_worker_health(self, worker_id: uuid.UUID) -> bool:
        """检查 Worker 健康状态"""
        worker = await self.db.fetch_one(
            "SELECT * FROM workers WHERE id = $1",
            worker_id
        )

        if not worker:
            return False

        # 检查心跳
        last_heartbeat = worker["last_heartbeat"]
        if (datetime.utcnow() - last_heartbeat).total_seconds() > 60:
            # Worker 超时，标记为离线
            await self.db.execute(
                "UPDATE workers SET status = 'offline' WHERE id = $1",
                worker_id
            )

            # 重新调度该 Worker 上的 Job
            await self._reschedule_worker_jobs(worker_id)

            return False

        return True

    async def _reschedule_worker_jobs(self, worker_id: uuid.UUID):
        """重新调度 Worker 上的所有 Job"""
        running_jobs = await self.db.fetch(
            """
            UPDATE jobs
            SET status = 'ready', worker_id = NULL
            WHERE worker_id = $1 AND status = 'running'
            RETURNING id
            """,
            worker_id
        )

        for job in running_jobs:
            logger.info(f"Rescheduling job {job['id']} due to worker failure")
```

### Job 超时处理

```python
async def check_job_timeouts(self):
    """检查 Job 超时"""
    timeout_jobs = await self.db.fetch(
        """
        UPDATE jobs
        SET status = 'failed',
            error_message = 'Job timeout'
        WHERE status = 'running'
        AND started_at < NOW() - (timeout_seconds || ' seconds')::interval
        RETURNING id, worker_id
        """
    )

    for job in timeout_jobs:
        logger.warning(f"Job {job['id']} timed out")

        # 通知 Worker 停止
        await self._notify_worker_stop(job["worker_id"], job["id"])
```

## 性能优化

1. **批量操作**: 一次处理多个 Job
2. **预取**: 预先获取可能需要的 Worker 信息
3. **缓存**: 缓存 Worker 状态，减少数据库查询
4. **并行调度**: 使用 asyncio 并发处理

## 监控指标

1. **调度延迟**: 从 Job ready 到 dispatched 的时间
2. **Worker 利用率**: CPU、内存、GPU 使用率
3. **队列深度**: 各模块队列长度
4. **吞吐量**: 每分钟完成的 Job 数
5. **失败率**: Job 失败率、Worker 故障率

## 后续决策

- 是否支持抢占式调度（高优先级任务抢占低优先级）
- 是否支持任务拆分（大任务拆成小任务）
- 多机房/多数据中心调度策略
