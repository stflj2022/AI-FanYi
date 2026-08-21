"""
调度器核心

负责依赖解析、资源匹配和任务分发
"""
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Set, Any
from loguru import logger

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Job,
    JobStatus,
    Worker,
    WorkerStatus,
    WorkerType,
    Project,
    ProjectStatus,
)
from .jwt_handler import JWTHandler


class DependencyResolver:
    """依赖解析器"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_dependencies(self, project_id: uuid.UUID) -> List[Job]:
        """
        解析项目依赖关系，返回可执行的作业列表

        Args:
            project_id: 项目 ID

        Returns:
            可执行的作业列表（按优先级排序）
        """
        # 获取所有作业
        result = await self.db.execute(
            select(Job).where(Job.project_id == project_id)
        )
        jobs = result.scalars().all()

        # 构建依赖图
        job_map = {job.id: job for job in jobs}
        ready_jobs: List[Job] = []

        for job in jobs:
            if await self._is_job_ready(job, job_map):
                ready_jobs.append(job)

        # 按创建时间排序
        ready_jobs.sort(key=lambda j: j.created_at)

        return ready_jobs

    async def _is_job_ready(self, job: Job, job_map: Dict[uuid.UUID, Job]) -> bool:
        """检查作业是否准备就绪"""
        if job.status not in [JobStatus.PENDING, JobStatus.FAILED]:
            return False

        # 检查依赖是否完成
        if job.depends_on:
            for dep_id in job.depends_on:
                dep_job = job_map.get(dep_id)
                if not dep_job or dep_job.status != JobStatus.COMPLETED:
                    return False

        return True

    async def get_ready_jobs(self, project_id: uuid.UUID) -> List[Job]:
        """获取准备好的作业"""
        return await self.resolve_dependencies(project_id)

    async def check_circular_dependency(self, project_id: uuid.UUID) -> Optional[List[uuid.UUID]]:
        """检查循环依赖，返回循环路径或 None"""
        result = await self.db.execute(
            select(Job).where(Job.project_id == project_id)
        )
        jobs = result.scalars().all()

        # 构建邻接表
        graph: Dict[uuid.UUID, List[uuid.UUID]] = {}
        for job in jobs:
            graph[job.id] = job.depends_on or []

        # DFS 检测环
        visited: Set[uuid.UUID] = set()
        rec_stack: Set[uuid.UUID] = set()
        path: List[uuid.UUID] = []

        def dfs(node: uuid.UUID) -> Optional[List[uuid.UUID]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    # 找到环
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            path.pop()
            rec_stack.remove(node)
            return None

        for job in jobs:
            if job.id not in visited:
                cycle = dfs(job.id)
                if cycle:
                    return cycle

        return None


class ResourceMatcher:
    """资源匹配器"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_best_worker(
        self,
        job: Job,
        require_gpu: bool = False
    ) -> Optional[Worker]:
        """
        找到最适合的 Worker

        Args:
            job: 作业
            require_gpu: 是否需要 GPU

        Returns:
            最佳 Worker 或 None
        """
        # 获取可用 Worker
        query = select(Worker).where(
            and_(
                Worker.status == WorkerStatus.IDLE,
                Worker.current_job_id.is_(None)
            )
        )

        # GPU 过滤
        if require_gpu:
            query = query.where(
                and_(
                    Worker.type == WorkerType.GPU,
                    Worker.gpu_count > 0
                )
            )
        else:
            query = query.where(Worker.type != WorkerType.GPU)

        result = await self.db.execute(query)
        workers = result.scalars().all()

        if not workers:
            return None

        # 计算匹配分数
        scored_workers = [
            (worker, await self._score_worker_job_match(worker, job))
            for worker in workers
        ]

        # 返回分数最高的
        scored_workers.sort(key=lambda x: x[1], reverse=True)
        return scored_workers[0][0] if scored_workers else None

    async def _score_worker_job_match(
        self,
        worker: Worker,
        job: Job
    ) -> float:
        """计算 Worker 和 Job 的匹配分数"""
        score = 0.0

        # 资源匹配 (40%)
        if worker.cpu_cores >= 4:
            score += 20
        if worker.memory_gb >= 16:
            score += 20

        # 能力匹配 (40%)
        if worker.capabilities:
            modules = worker.capabilities.get("modules", [])
            if job.module_id in modules:
                score += 40

        # 历史表现 (20%)
        total = worker.jobs_completed + worker.jobs_failed
        if total > 0:
            success_rate = worker.jobs_completed / total
            score += success_rate * 20

        return score

    async def check_resource_sufficient(
        self,
        worker: Worker,
        required_cpu: int = 2,
        required_memory: int = 8,
        require_gpu: bool = False
    ) -> bool:
        """检查资源是否足够"""
        if require_gpu:
            if worker.gpu_count == 0:
                return False

        if worker.cpu_cores < required_cpu:
            return False

        if worker.memory_gb < required_memory:
            return False

        return True


class DispatchEngine:
    """分发引擎"""

    def __init__(self, db: AsyncSession, jwt_handler: JWTHandler):
        self.db = db
        self.jwt_handler = jwt_handler

    async def dispatch_job(self, job: Job, worker: Worker) -> Dict[str, Any]:
        """
        分发作业到 Worker

        Args:
            job: 作业
            worker: Worker

        Returns:
            分发结果
        """
        # 更新作业状态
        job.status = JobStatus.SCHEDULED
        job.worker_id = worker.id
        job.scheduled_at = datetime.utcnow()

        # 更新 Worker 状态
        worker.status = WorkerStatus.BUSY
        worker.current_job_id = job.id

        await self.db.flush()

        # 生成分发信息
        dispatch_info = {
            "job_id": str(job.id),
            "project_id": str(job.project_id),
            "module_id": job.module_id,
            "config": job.config or {},
            "input_artifacts": job.input_artifacts or [],
            "worker_token": self.jwt_handler.generate_token(str(worker.id)),
        }

        return dispatch_info

    async def _get_input_artifacts(self, job: Job) -> List[Dict[str, Any]]:
        """获取输入 Artifact"""
        # TODO: 从数据库获取 Artifact 信息
        return []

    async def _generate_download_url(self, artifact_id: uuid.UUID) -> str:
        """生成下载 URL"""
        # TODO: 生成预签名 URL
        return f"/api/v1/artifacts/{artifact_id}/download"


class Scheduler:
    """调度器主类"""

    def __init__(
        self,
        db: AsyncSession,
        jwt_handler: JWTHandler,
        cycle_interval: int = 1
    ):
        self.db = db
        self.jwt_handler = jwt_handler
        self.cycle_interval = cycle_interval

        self.dependency_resolver = DependencyResolver(db)
        self.resource_matcher = ResourceMatcher(db)
        self.dispatch_engine = DispatchEngine(db, jwt_handler)

        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("Scheduler is already running")
            return

        self._running = True
        logger.info("Scheduler started")

        self._task = asyncio.create_task(self._schedule_loop())

    async def stop(self):
        """停止调度器"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Scheduler stopped")

    async def _schedule_loop(self):
        """调度循环"""
        while self._running:
            try:
                await self._schedule_cycle()
            except Exception as e:
                logger.error(f"Schedule cycle error: {e}", exc_info=True)

            await asyncio.sleep(self.cycle_interval)

    async def _schedule_cycle(self):
        """执行一次调度周期"""
        # 获取所有运行中的项目
        result = await self.db.execute(
            select(Project).where(Project.status == ProjectStatus.PROCESSING)
        )
        projects = result.scalars().all()

        for project in projects:
            await self._schedule_project(project)

    async def _schedule_project(self, project: Project):
        """调度单个项目"""
        # 获取准备好的作业
        ready_jobs = await self.dependency_resolver.get_ready_jobs(project.id)

        for job in ready_jobs:
            # 找到合适的 Worker
            require_gpu = job.module_id in ["M09"]  # M09 需要 GPU
            worker = await self.resource_matcher.find_best_worker(job, require_gpu)

            if worker:
                # 分发作业
                await self.dispatch_engine.dispatch_job(job, worker)
                logger.info(f"Dispatched job {job.id} to worker {worker.id}")
            else:
                # 没有可用 Worker，等待下一轮
                logger.debug(f"No available worker for job {job.id}")
