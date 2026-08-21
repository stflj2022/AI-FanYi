"""
Worker 管理器

负责 Worker 注册、心跳监控、状态跟踪和指令下发
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Worker,
    WorkerStatus,
    WorkerType,
    Job,
    JobStatus,
)
from .jwt_handler import JWTHandler


class WorkerManager:
    """Worker 管理器"""

    def __init__(
        self,
        db: AsyncSession,
        heartbeat_timeout: int = 60,
        heartbeat_interval: int = 10,
        jwt_handler: Optional[JWTHandler] = None
    ):
        """
        初始化 Worker 管理器

        Args:
            db: 数据库会话
            heartbeat_timeout: 心跳超时时间（秒）
            heartbeat_interval: 心跳间隔（秒）
            jwt_handler: JWT 处理器（可选）
        """
        self.db = db
        self.heartbeat_timeout = heartbeat_timeout
        self.heartbeat_interval = heartbeat_interval
        self.jwt_handler = jwt_handler or JWTHandler()

    async def register_worker(
        self,
        name: str,
        worker_type: WorkerType = WorkerType.CPU,
        capabilities: Dict[str, Any] = None,
        cpu_cores: int = 4,
        memory_gb: int = 16,
        gpu_count: int = 0,
        gpu_memory_gb: int = 0,
        host: str = "localhost",
        port: int = 8001
    ) -> Dict[str, Any]:
        """
        注册 Worker

        Args:
            name: Worker 名称
            worker_type: Worker 类型
            capabilities: 能力列表
            cpu_cores: CPU 核心数
            memory_gb: 内存 GB
            gpu_count: GPU 数量
            gpu_memory_gb: GPU 显存
            host: 主机地址
            port: 端口

        Returns:
            Worker 信息和 Token
        """
        # 检查是否已存在
        existing = await self.db.execute(
            select(Worker).where(Worker.name == name)
        )
        existing_worker = existing.scalar_one_or_none()

        if existing_worker:
            # 已存在，检查状态
            if existing_worker.status == WorkerStatus.OFFLINE:
                # 重新激活
                await self.db.execute(
                    update(Worker)
                    .where(Worker.id == existing_worker.id)
                    .values(
                        status=WorkerStatus.STARTING,
                        host=host,
                        port=port,
                        updated_at=datetime.utcnow()
                    )
                )
                await self.db.commit()

                token = self.jwt_handler.generate_token(str(existing_worker.id))
                return self._worker_to_dict(existing_worker, token=token)
            else:
                return {
                    "error": "WORKER_ALREADY_EXISTS",
                    "message": f"Worker '{name}' is already registered and active"
                }

        # 创建新 Worker
        worker = Worker(
            name=name,
            status=WorkerStatus.STARTING,
            type=worker_type,
            capabilities=capabilities or {},
            cpu_cores=cpu_cores,
            memory_gb=memory_gb,
            gpu_count=gpu_count,
            gpu_memory_gb=gpu_memory_gb,
            host=host,
            port=port,
            last_heartbeat=datetime.utcnow(),
            heartbeat_interval_seconds=self.heartbeat_interval
        )

        self.db.add(worker)
        await self.db.flush()
        await self.db.commit()

        # 生成真实 JWT Token
        worker_token = self.jwt_handler.generate_token(str(worker.id))

        logger.info(f"Worker registered: {name} ({worker.id})")

        return self._worker_to_dict(worker, token=worker_token)

    async def handle_heartbeat(
        self,
        worker_id: uuid.UUID,
        status: str = "idle",
        current_job_id: Optional[uuid.UUID] = None,
        statistics: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        处理 Worker 心跳

        Args:
            worker_id: Worker ID
            status: Worker 状态
            current_job_id: 当前作业 ID
            statistics: 统计信息

        Returns:
            响应，包含待处理指令
        """
        # 检查 Worker 是否存在
        result = await self.db.execute(
            select(Worker).where(Worker.id == worker_id)
        )
        worker = result.scalar_one_or_none()

        if not worker:
            return {
                "error": "WORKER_NOT_FOUND",
                "message": "Worker not found"
            }

        # 更新状态
        await self.db.execute(
            update(Worker)
            .where(Worker.id == worker_id)
            .values(
                status=WorkerStatus(status),
                current_job_id=current_job_id,
                last_heartbeat=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        )

        # 更新统计字段（jobs_completed / jobs_failed / total_runtime_seconds）
        if statistics:
            update_values = {
                "last_heartbeat": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            if "jobs_completed" in statistics:
                update_values["jobs_completed"] = int(statistics["jobs_completed"])
            if "jobs_failed" in statistics:
                update_values["jobs_failed"] = int(statistics["jobs_failed"])
            if "total_runtime_seconds" in statistics:
                update_values["total_runtime_seconds"] = int(statistics["total_runtime_seconds"])
            if update_values:
                await self.db.execute(
                    update(Worker)
                    .where(Worker.id == worker_id)
                    .values(**update_values)
                )

        await self.db.commit()

        # 检查待处理指令
        pending_commands = await self._get_pending_commands(worker_id)

        logger.debug(f"Heartbeat from {worker.name}: status={status}")

        return {
            "success": True,
            "pending_commands": pending_commands
        }

    async def get_worker(
        self,
        worker_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        获取 Worker 信息

        Args:
            worker_id: Worker ID

        Returns:
            Worker 信息或 None
        """
        result = await self.db.execute(
            select(Worker).where(Worker.id == worker_id)
        )
        worker = result.scalar_one_or_none()

        if worker:
            return self._worker_to_dict(worker)

        return None

    async def list_workers(
        self,
        status: Optional[WorkerStatus] = None,
        worker_type: Optional[WorkerType] = None
    ) -> List[Dict[str, Any]]:
        """
        列出 Workers

        Args:
            status: 状态过滤
            worker_type: 类型过滤

        Returns:
            Worker 列表
        """
        query = select(Worker)

        if status:
            query = query.where(Worker.status == status)

        if worker_type:
            query = query.where(Worker.type == worker_type)

        query = query.order_by(Worker.created_at.desc())

        result = await self.db.execute(query)
        workers = result.scalars().all()

        return [self._worker_to_dict(w) for w in workers]

    async def unregister_worker(
        self,
        worker_id: uuid.UUID
    ) -> bool:
        """
        注销 Worker

        Args:
            worker_id: Worker ID

        Returns:
            是否成功
        """
        result = await self.db.execute(
            select(Worker).where(Worker.id == worker_id)
        )
        worker = result.scalar_one_or_none()

        if not worker:
            return False

        # 检查是否有运行中的作业
        if worker.current_job_id:
            logger.warning(
                f"Worker {worker.name} has running job {worker.current_job_id}, "
                "can only unregister after job completes or is cancelled"
            )
            return False

        # 标记为下线
        await self.db.execute(
            update(Worker)
            .where(Worker.id == worker_id)
            .values(status=WorkerStatus.STOPPING)
        )
        await self.db.commit()

        logger.info(f"Worker unregistered: {worker.name} ({worker_id})")

        return True

    async def check_timeouts(self):
        """检查并处理超时的 Worker"""
        timeout_threshold = datetime.utcnow() - timedelta(
            seconds=self.heartbeat_timeout
        )

        result = await self.db.execute(
            select(Worker)
            .where(Worker.status == WorkerStatus.BUSY)
            .where(Worker.last_heartbeat < timeout_threshold)
        )
        timeout_workers = result.scalars().all()

        for worker in timeout_workers:
            logger.warning(
                f"Worker timeout: {worker.name} "
                f"(last heartbeat: {worker.last_heartbeat})"
            )

            # 重新调度该 Worker 上的 Job
            if worker.current_job_id:
                await self._reschedule_job(worker.id, worker.current_job_id)

            # 标记为离线
            await self.db.execute(
                update(Worker)
                .where(Worker.id == worker.id)
                .values(status=WorkerStatus.OFFLINE)
            )
            await self.db.commit()

    async def _reschedule_job(
        self,
        worker_id: uuid.UUID,
        job_id: uuid.UUID
    ):
        """
        重新调度作业

        Args:
            worker_id: Worker ID
            job_id: Job ID
        """
        logger.info(f"Rescheduling job {job_id} from worker {worker_id}")

        # 标记 Job 为待处理
        await self.db.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                status=JobStatus.PENDING,
                worker_id=None,
                retry_count=Job.retry_count + 1
            )
        )

        # 更新 Worker 状态
        await self.db.execute(
            update(Worker)
            .where(Worker.id == worker_id)
            .values(
                current_job_id=None,
                status=WorkerStatus.IDLE
            )
        )

        await self.db.commit()

    async def _get_pending_commands(
        self,
        worker_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        获取待处理的指令

        从作业表中查询已调度给该 Worker 且尚未开始的作业，
        将其转换为 `execute_job` 指令下发。

        Args:
            worker_id: Worker ID

        Returns:
            指令列表
        """
        result = await self.db.execute(
            select(Job).where(
                Job.worker_id == worker_id,
                Job.status == JobStatus.SCHEDULED,
            )
        )
        jobs = result.scalars().all()

        commands = []
        for job in jobs:
            commands.append(
                {
                    "command": "execute_job",
                    "job_id": str(job.id),
                    "project_id": str(job.project_id),
                    "module_id": job.module_id,
                    "input_artifacts": job.input_artifacts or [],
                    "config": {},
                }
            )

        return commands

    def _worker_to_dict(
        self,
        worker: Worker,
        token: str = None
    ) -> Dict[str, Any]:
        """
        将 Worker 模型转换为字典

        Args:
            worker: Worker 模型
            token: Worker Token（可选）

        Returns:
            字典形式的 Worker 信息
        """
        return {
            "id": str(worker.id),
            "name": worker.name,
            "status": worker.status.value,
            "type": worker.type.value,
            "capabilities": worker.capabilities,
            "cpu_cores": worker.cpu_cores,
            "memory_gb": worker.memory_gb,
            "gpu_count": worker.gpu_count,
            "gpu_memory_gb": worker.gpu_memory_gb,
            "jobs_completed": worker.jobs_completed,
            "jobs_failed": worker.jobs_failed,
            "total_runtime_seconds": worker.total_runtime_seconds,
            "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
            "created_at": worker.created_at.isoformat(),
            "updated_at": worker.updated_at.isoformat(),
            "host": worker.host,
            "port": worker.port,
            "worker_token": token
        }


class WorkerCommandType:
    """Worker 指令类型"""
    CANCEL_JOB = "cancel_job"
    PAUSE_JOB = "pause_job"
    RESUME_JOB = "resume_job"
    UPDATE_CONFIG = "update_config"
    SHUTDOWN = "shutdown"
