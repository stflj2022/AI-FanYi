"""Workflow Executor - 工作流执行器

执行 Planner 生成的 ExecutionPlan，严格采用：
Module → Artifact → Checkpoint → 释放资源 → 下一个 Module

参考：计划书 2 二十五、二十六节
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Set
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from ..models import Job, JobStatus, Worker, WorkerStatus
from ..artifact_registry import ArtifactRegistry
from .workflow_planner import ExecutionPlan, ExecutionStep, ExecutionMode
from .task_context import TaskContext
from .capability_matrix import CapabilityMatrix
from .workflow_selector import WorkflowType

logger = logging.getLogger(__name__)


class ExecutionState:
    """执行状态"""

    def __init__(self):
        self.completed_steps: Set[str] = set()
        self.failed_steps: Set[str] = set()
        self.current_step: Optional[str] = None
        self.artifacts: Dict[str, Path] = {}
        self.checkpoint_data: Dict = {}
        self.start_time: Optional[datetime] = None

    def is_step_completed(self, module: str) -> bool:
        """检查步骤是否完成"""
        return module in self.completed_steps

    def mark_step_completed(self, module: str, artifact_path: Optional[Path] = None):
        """标记步骤完成"""
        self.completed_steps.add(module)
        if artifact_path:
            self.artifacts[module] = artifact_path

    def mark_step_failed(self, module: str):
        """标记步骤失败"""
        self.failed_steps.add(module)

    def get_checkpoint(self) -> Dict:
        """获取检查点数据"""
        return {
            "completed_steps": list(self.completed_steps),
            "failed_steps": list(self.failed_steps),
            "current_step": self.current_step,
            "artifacts": {k: str(v) for k, v in self.artifacts.items()},
            "start_time": self.start_time.isoformat() if self.start_time else None,
        }

    def load_checkpoint(self, checkpoint_data: Dict):
        """加载检查点数据"""
        self.completed_steps = set(checkpoint_data.get("completed_steps", []))
        self.failed_steps = set(checkpoint_data.get("failed_steps", []))
        self.current_step = checkpoint_data.get("current_step")
        self.artifacts = {
            k: Path(v) if isinstance(v, str) else v
            for k, v in checkpoint_data.get("artifacts", {}).items()
        }
        if checkpoint_data.get("start_time"):
            self.start_time = datetime.fromisoformat(checkpoint_data["start_time"])


class WorkflowExecutor:
    """工作流执行器

    执行 ExecutionPlan，管理资源、Artifact 和检查点。
    """

    # 模块到 Worker 的映射
    MODULE_WORKER_MAP = {
        "M01": "media_intake",
        "M02": "research",
        "M03": "subtitle",
        "M04": "character_db",
        "M05": "audio_analysis",
        "M06": "speaker_mapping",
        "M07": "dialogue_intelligence",
        "M08": "prosody_planning",
        "M09": "voice_synthesis",
        "M10": "audio_mixing",
        "M11": "video_assembly",
        "M12": "video_encapsulation",
        "M13": "qa",
        "M14": "archive",
    }

    def __init__(
        self,
        db: AsyncSession,
        artifact_registry: ArtifactRegistry,
        project_root: Path,
    ):
        """初始化执行器

        Args:
            db: 数据库会话
            artifact_registry: Artifact 注册表
            project_root: 项目根目录
        """
        self.db = db
        self.artifact_registry = artifact_registry
        self.project_root = Path(project_root)
        self.state = ExecutionState()

    async def execute(
        self,
        execution_plan: ExecutionPlan,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix,
        resume_from_checkpoint: bool = False,
    ) -> Dict:
        """执行工作流

        Args:
            execution_plan: 执行计划
            task_context: 任务上下文
            capability_matrix: 能力矩阵
            resume_from_checkpoint: 是否从检查点恢复

        Returns:
            执行结果
        """
        # 加载检查点
        if resume_from_checkpoint:
            await self._load_checkpoint(task_context.project_id)

        self.state.start_time = datetime.now()
        logger.info(f"开始执行工作流: {execution_plan.plan_id}")

        # 按顺序执行步骤
        for step in execution_plan.steps:
            # 检查是否已完成
            if self.state.is_step_completed(step.module):
                logger.info(f"步骤 {step.module} 已完成，跳过")
                continue

            # 检查是否失败
            if step.module in self.state.failed_steps:
                logger.warning(f"步骤 {step.module} 之前失败，跳过")
                continue

            # 检查依赖
            if not self._are_dependencies_met(step, execution_plan):
                logger.error(f"步骤 {step.module} 的依赖未满足")
                raise RuntimeError(f"步骤 {step.module} 的依赖未满足")

            # 执行步骤
            self.state.current_step = step.module
            try:
                await self._execute_step(step, task_context, capability_matrix)
                self.state.mark_step_completed(step.module)
                await self._save_checkpoint(task_context.project_id)
            except Exception as e:
                logger.error(f"步骤 {step.module} 执行失败: {e}")
                self.state.mark_step_failed(step.module)
                await self._save_checkpoint(task_context.project_id)
                raise

        # 执行完成
        result = {
            "plan_id": execution_plan.plan_id,
            "status": "completed",
            "completed_steps": list(self.state.completed_steps),
            "failed_steps": list(self.state.failed_steps),
            "duration": (datetime.now() - self.state.start_time).total_seconds(),
            "artifacts": {k: str(v) for k, v in self.state.artifacts.items()},
        }

        logger.info(f"工作流执行完成: {execution_plan.plan_id}")
        return result

    async def _execute_step(
        self,
        step: ExecutionStep,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix,
    ):
        """执行单个步骤

        Args:
            step: 执行步骤
            task_context: 任务上下文
            capability_matrix: 能力矩阵
        """
        logger.info(f"执行步骤: {step.module} (模式: {step.mode})")

        # 根据执行模式处理
        if step.mode == ExecutionMode.SKIP:
            logger.info(f"步骤 {step.module} 跳过")
            return

        elif step.mode == ExecutionMode.LOAD:
            # 加载已有 Artifact
            artifact = await self._load_artifact(step.module, task_context)
            if artifact:
                self.state.artifacts[step.module] = artifact
            logger.info(f"步骤 {step.module} 已加载 Artifact")

        elif step.mode in [ExecutionMode.RUN_FULL, ExecutionMode.RUN_INCREMENTAL]:
            # 运行模块
            artifact_path = await self._run_module(
                step,
                task_context,
                capability_matrix,
            )
            if artifact_path:
                self.state.artifacts[step.module] = artifact_path
                # 注册 Artifact
                await self._register_artifact(
                    step.module,
                    artifact_path,
                    task_context,
                )

        logger.info(f"步骤 {step.module} 完成")

    async def _run_module(
        self,
        step: ExecutionStep,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix,
    ) -> Optional[Path]:
        """运行模块

        Args:
            step: 执行步骤
            task_context: 任务上下文
            capability_matrix: 能力矩阵

        Returns:
            Artifact 路径
        """
        # 获取 Worker 类型
        worker_type = self.MODULE_WORKER_MAP.get(step.module)
        if not worker_type:
            logger.error(f"未知模块: {step.module}")
            raise ValueError(f"未知模块: {step.module}")

        # 查找可用的 Worker
        worker = await self._find_available_worker(worker_type)
        if not worker:
            logger.error(f"没有可用的 {worker_type} Worker")
            raise RuntimeError(f"没有可用的 {worker_type} Worker")

        # 创建 Job
        job = await self._create_job(
            task_context.project_id,
            step.module,
            worker.id,
            step.mode,
            step.estimated_duration,
        )

        try:
            # 准备输入参数
            input_data = await self._prepare_input(
                step,
                task_context,
                capability_matrix,
            )

            # 分发任务给 Worker
            await self._dispatch_to_worker(job, worker, input_data)

            # 等待 Job 完成
            await self._wait_for_job_completion(job)

            # 获取输出 Artifact
            artifact_path = await self._get_job_artifact(job)
            return artifact_path

        finally:
            # 清理资源
            await self._cleanup_job(job)

    async def _find_available_worker(self, worker_type: str) -> Optional[Worker]:
        """查找可用的 Worker

        Args:
            worker_type: Worker 类型

        Returns:
            可用的 Worker
        """
        result = await self.db.execute(
            select(Worker).where(
                and_(
                    Worker.worker_type == worker_type,
                    Worker.status == WorkerStatus.IDLE,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _create_job(
        self,
        project_id: str,
        module: str,
        worker_id: uuid.UUID,
        mode: ExecutionMode,
        estimated_duration: Optional[float],
    ) -> Job:
        """创建 Job

        Args:
            project_id: 项目 ID
            module: 模块 ID
            worker_id: Worker ID
            mode: 执行模式
            estimated_duration: 预估时长

        Returns:
            创建的 Job
        """
        job = Job(
            project_id=project_id,
            worker_id=worker_id,
            module=module,
            status=JobStatus.PENDING,
            config={
                "mode": mode.value,
                "estimated_duration": estimated_duration,
            },
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def _prepare_input(
        self,
        step: ExecutionStep,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix,
    ) -> Dict:
        """准备输入数据

        Args:
            step: 执行步骤
            task_context: 任务上下文
            capability_matrix: 能力矩阵

        Returns:
            输入数据
        """
        input_data = {
            "project_id": str(task_context.project_id),
            "media_id": task_context.media_id,
            "task_type": task_context.task_type.value,
            "mode": step.mode.value,
        }

        # 添加依赖的 Artifact
        for dep in step.dependencies:
            if dep in self.state.artifacts:
                input_data[f"artifact_{dep}"] = str(self.state.artifacts[dep])

        return input_data

    async def _dispatch_to_worker(self, job: Job, worker: Worker, input_data: Dict):
        """分发任务给 Worker

        Args:
            job: Job
            worker: Worker
            input_data: 输入数据
        """
        # 更新 Job 状态
        job.status = JobStatus.DISPATCHED
        job.started_at = datetime.utcnow()
        await self.db.commit()

        # TODO: 实际的分发逻辑（通过 WebSocket 或 HTTP API）
        # 这里只是模拟
        logger.info(f"分发 Job {job.id} 给 Worker {worker.id}")

        # 模拟执行
        await asyncio.sleep(1)

        # 更新 Job 状态
        job.status = JobStatus.RUNNING
        await self.db.commit()

    async def _wait_for_job_completion(self, job: Job, timeout: float = 3600):
        """等待 Job 完成

        Args:
            job: Job
            timeout: 超时时间（秒）
        """
        # TODO: 实际的等待逻辑（通过轮询或 WebSocket 通知）
        # 这里只是模拟
        logger.info(f"等待 Job {job.id} 完成")

        # 模拟执行
        await asyncio.sleep(1)

        # 更新 Job 状态
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        await self.db.commit()

    async def _get_job_artifact(self, job: Job) -> Optional[Path]:
        """获取 Job 的输出 Artifact

        Args:
            job: Job

        Returns:
            Artifact 路径
        """
        # TODO: 实际的 Artifact 获取逻辑
        # 这里只是模拟
        artifact_path = self.project_root / job.project_id / "artifacts" / f"{job.module}.json"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        return artifact_path

    async def _cleanup_job(self, job: Job):
        """清理 Job 资源

        Args:
            job: Job
        """
        # TODO: 实际的资源清理逻辑
        logger.info(f"清理 Job {job.id} 资源")

    async def _load_artifact(self, module: str, task_context: TaskContext) -> Optional[Path]:
        """加载已有 Artifact

        Args:
            module: 模块 ID
            task_context: 任务上下文

        Returns:
            Artifact 路径
        """
        # 从 Artifact Registry 查找
        artifacts = await self.artifact_registry.list_artifacts(
            project_id=task_context.project_id,
            module=module,
        )

        if artifacts:
            # 返回最新的 Artifact
            latest = max(artifacts, key=lambda a: a.created_at)
            return Path(latest.file_path)

        return None

    async def _register_artifact(
        self,
        module: str,
        artifact_path: Path,
        task_context: TaskContext,
    ):
        """注册 Artifact

        Args:
            module: 模块 ID
            artifact_path: Artifact 路径
            task_context: 任务上下文
        """
        await self.artifact_registry.create_artifact(
            project_id=task_context.project_id,
            module=module,
            file_path=str(artifact_path),
            metadata={"created_by": "workflow_executor"},
        )

    def _are_dependencies_met(self, step: ExecutionStep, execution_plan: ExecutionPlan) -> bool:
        """检查依赖是否满足

        Args:
            step: 执行步骤
            execution_plan: 执行计划

        Returns:
            是否满足依赖
        """
        for dep in step.dependencies:
            if not self.state.is_step_completed(dep):
                return False
        return True

    async def _save_checkpoint(self, project_id: str):
        """保存检查点

        Args:
            project_id: 项目 ID
        """
        checkpoint_path = self.project_root / project_id / "checkpoint.json"
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        import json
        with open(checkpoint_path, 'w') as f:
            json.dump(self.state.get_checkpoint(), f, indent=2)

        logger.info(f"检查点已保存: {checkpoint_path}")

    async def _load_checkpoint(self, project_id: str):
        """加载检查点

        Args:
            project_id: 项目 ID
        """
        checkpoint_path = self.project_root / project_id / "checkpoint.json"

        if not checkpoint_path.exists():
            logger.info(f"检查点不存在: {checkpoint_path}")
            return

        import json
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)

        self.state.load_checkpoint(checkpoint_data)
        logger.info(f"检查点已加载: {checkpoint_path}")
