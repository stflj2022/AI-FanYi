"""
执行引擎（阶段 B：完整流水线 + 动态调度）

轮询 orchestrator 数据库中的 pending/scheduled 配音任务，执行对应模块并更新状态。

当前实现：
- 动态工作流选择：基于任务上下文和能力矩阵自动选择 QUICK/STANDARD/PRODUCTION 工作流
- 智能执行计划：根据已有 Artifact 决定 LOAD/SKIP/RUN_INCREMENTAL/RUN_FULL
- 断点续跑：从失败模块继续执行
- M01 媒体分析：从 MinIO 下载输入媒体 → FFprobe 分析 → 写入 media_analysis artifact
- 完整流水线：执行 M01~M14 完整流程，产出最终配音视频
- 状态流转：PENDING → RUNNING → COMPLETED / FAILED
- 任务所属项目自动置为 PROCESSING（与 orchestrator 调度语义一致）

运行：
    DATABASE_URL=postgresql+asyncpg://... python -m filmdub.orchestrator.job_runner [轮询间隔秒]
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import select

from filmdub.core.orchestrator_db import AsyncSessionLocal
from filmdub.core.models import (
    Job,
    JobStatus,
    ProjectRecord as Project,
    ProjectStatus,
    MediaAsset,
)
from filmdub.workers.media_intake.probe import FFprobeParser
from filmdub.workers.common import save_json_artifact
from .full_pipeline_executor import FullPipelineExecutor
from .workflow.task_context import TaskContext, TaskType, QualityRequirement
from .workflow.asset_discovery import AssetDiscovery
from .workflow.capability_matrix import CapabilityMatrix, CapabilityBuilder
from .workflow.workflow_selector import WorkflowSelector
from .workflow.workflow_planner import WorkflowPlanner, ExecutionMode
from .workflow.dependency_resolver import DependencyResolver

# 模块到人性化文案的映射
MODULE_STAGE_MAP = {
    "M01": "正在导入视频媒体",
    "M02": "正在分离音频和背景音",
    "M03": "正在获取字幕信息",
    "M05": "正在转写对白文字",
    "M04": "正在建立人物数据库",
    "M06": "正在识别说话人物",
    "M07": "正在翻译对白为中文",
    "M08": "正在规划语音韵律",
    "M09": "正在合成中文语音",
    "M10": "正在混音处理",
    "M11": "正在组装视频",
    "M12": "正在封装最终视频",
    "M13": "正在进行质量检查",
    "M14": "正在归档项目",
}

# 错误人性化文案映射
ERROR_MESSAGE_MAP = {
    "M01": "视频导入失败，请检查视频格式是否支持",
    "M02": "音频分离失败，系统正在自动重试",
    "M03": "字幕获取失败，将使用自动转写",
    "M05": "对白转写失败，系统正在自动重试",
    "M04": "人物数据库创建失败，请稍后重试",
    "M06": "说话人识别失败，系统正在自动重试",
    "M07": "翻译服务暂时不可用，系统正在自动重试",
    "M08": "韵律规划失败，使用默认参数继续",
    "M09": "语音合成暂时遇到问题，系统正在自动重试",
    "M10": "音频混音失败，系统正在自动重试",
    "M11": "视频组装失败，系统正在自动重试",
    "M12": "视频封装失败，请检查输出格式",
    "M13": "质量检查失败，请查看详细报告",
    "M14": "项目归档失败，请检查存储空间",
}

logger = logging.getLogger(__name__)

MINIO_BUCKET = "filmdub-uploads"


class JobRunner:
    """动态任务执行引擎
    
    集成 Layer 0 动态调度：
    - Task Context → Asset Discovery → Capability Matrix
    - Workflow Selector → 选择 QUICK/STANDARD/PRODUCTION
    - Workflow Planner → 生成执行计划（LOAD/SKIP/RUN_INCREMENTAL/RUN_FULL）
    - Executor → 执行模块，支持断点续跑
    """

    def __init__(self, poll_interval: float = 5.0, work_dir: str = "/tmp/filmdub_runner"):
        self.poll_interval = poll_interval
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.ffprobe = FFprobeParser()
        self.minio = self._init_minio()
        
        # Layer 0 组件
        self.asset_discovery = AssetDiscovery(self.work_dir)
        self.workflow_selector = WorkflowSelector()
        self.dependency_resolver = DependencyResolver()
        self.workflow_planner = WorkflowPlanner(self.dependency_resolver)

    @staticmethod
    def _init_minio():
        """初始化 MinIO 客户端（环境变量可覆盖）"""
        from minio import Minio

        return Minio(
            os.environ.get("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin123"),
            secure=False,
        )

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------
    async def run(self) -> None:
        logger.info(f"Job Runner started, poll interval {self.poll_interval}s")
        while True:
            try:
                await self._process_cycle()
            except Exception as e:
                logger.error(f"Cycle error: {e}", exc_info=True)
            await asyncio.sleep(self.poll_interval)

    async def _process_cycle(self) -> None:
        """处理一轮待执行任务"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Job)
                .where(Job.status.in_([JobStatus.PENDING, JobStatus.SCHEDULED]))
                .order_by(Job.created_at)
            )
            jobs = result.scalars().all()
            for job in jobs:
                await self._process_job(db, job)

    async def _process_job(self, db, job: Job) -> None:
        """执行单个任务：M01 媒体分析 或 动态工作流"""
        logger.info(f"Processing job {job.id} ({job.name}) module={job.module_id}")

        # 标 RUNNING + 项目置 PROCESSING
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        if job.project_id:
            project = await db.get(Project, job.project_id)
            if project and project.status == ProjectStatus.PENDING:
                project.status = ProjectStatus.PROCESSING
        await db.commit()

        try:
            # 判断执行模式
            if job.module_id == "FULL_PIPELINE":
                # 使用动态工作流执行
                result = await self._run_dynamic_workflow(db, job)
            elif job.module_id == "M01":
                # 兼容旧版 M01 执行
                analysis = await self._run_m01(db, job)
                result = {"media_analysis": analysis}
            else:
                # 默认使用动态工作流
                result = await self._run_dynamic_workflow(db, job)

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            # 记录输出 artifacts
            output_arts = self._collect_output_artifacts(job, result)
            # 保存 QA 评分到 job.config（供 qa-report 接口展示）
            if result.get("qa_score") is not None:
                if not job.config:
                    job.config = {}
                job.config["qa_score"] = result["qa_score"]
            # 上传最终视频到 MinIO（供 Web UI 在线播放/下载）
            final_obj = self._upload_final_video(job, result)
            if final_obj:
                output_arts.append(f"final_video:{final_obj}")
            job.output_artifacts = (job.output_artifacts or []) + output_arts
            logger.info(f"Job {job.id} completed: {len(output_arts)} artifacts")
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)[:2000]
            logger.error(f"Job {job.id} failed: {e}", exc_info=True)
        await db.commit()

    def _upload_final_video(self, job: Job, result: dict) -> Optional[str]:
        """
        将最终配音视频上传到 MinIO（供 Web UI 展示/下载）

        Args:
            job: 任务对象
            result: 执行结果（含 work_dir）

        Returns:
            MinIO object 名；无成品视频时返回 None
        """
        work_dir = result.get("work_dir")
        if not work_dir:
            return None
        out_dir = Path(work_dir) / "output"
        for name in ("final_encapsulated.mp4", "final_dubbed.mp4"):
            video_path = out_dir / name
            if video_path.exists():
                object_name = f"output/{job.id}/{name}"
                self.minio.fput_object(MINIO_BUCKET, object_name, str(video_path))
                logger.info(f"Final video uploaded: {object_name}")
                return object_name
        return None

    # ------------------------------------------------------------------
    # M01 媒体分析
    # ------------------------------------------------------------------
    async def _run_m01(self, db, job: Job) -> dict:
        """
        执行 M01 媒体分析

        从 input_artifacts 解析媒体资产 → MinIO 下载 → FFprobe 分析 → 写 manifest artifact
        """
        media_ids = job.input_artifacts or []
        if not media_ids:
            raise ValueError("任务无输入媒体（input_artifacts 为空）")

        media_id = str(media_ids[0])
        media_asset: Optional[MediaAsset] = await db.get(MediaAsset, media_id)
        if media_asset is None:
            raise ValueError(f"媒体资产不存在: {media_id}")

        # 从 MinIO 下载
        local_path = self.work_dir / f"{media_id[:8]}_{media_asset.original_filename}"
        self.minio.fget_object(MINIO_BUCKET, media_asset.storage_path, str(local_path))
        logger.info(f"Downloaded {media_asset.storage_path} -> {local_path}")

        # FFprobe 分析
        probe_data = self.ffprobe.probe(local_path)
        analysis = {
            "job_id": str(job.id),
            "media_asset_id": media_id,
            "filename": media_asset.original_filename,
            "duration_seconds": self.ffprobe.get_duration(probe_data),
            "format": probe_data.get("format", {}),
            "streams": probe_data.get("streams", []),
            "video_streams": self.ffprobe.get_video_streams(probe_data),
            "audio_streams": self.ffprobe.get_audio_streams(probe_data),
            "subtitle_streams": self.ffprobe.get_subtitle_streams(probe_data),
        }

        # 写 media_analysis artifact（项目 artifacts 目录）
        project_id = str(job.project_id) if job.project_id else "no-project"
        artifact_path = save_json_artifact(project_id, "media_analysis", analysis)
        logger.info(f"Media analysis artifact: {artifact_path}")

        return analysis

    def _collect_output_artifacts(self, job: Job, result: dict) -> list:
        """收集输出 artifacts
        
        Args:
            job: 任务对象
            result: 执行结果
            
        Returns:
            artifact 列表
        """
        output_arts = []
        if "final_video" in result:
            output_arts.append(f"final_video:{result.get('final_video', '')}")
        if "work_dir" in result:
            output_arts.append(f"work_dir:{result.get('work_dir', '')}")
        if "media_analysis" in result:
            output_arts.append(f"media_analysis:{job.id}")
        return output_arts

    # ------------------------------------------------------------------
    # 动态工作流执行
    # ------------------------------------------------------------------
    async def _run_dynamic_workflow(self, db, job: Job) -> dict:
        """
        执行动态工作流
        
        流程：
        1. 构建任务上下文（Task Context）
        2. 资产发现（Asset Discovery）
        3. 构建能力矩阵（Capability Matrix）
        4. 选择工作流（Workflow Selector）
        5. 生成执行计划（Workflow Planner）
        6. 执行计划（Executor）
        """
        media_ids = job.input_artifacts or []
        if not media_ids:
            raise ValueError("任务无输入媒体（input_artifacts 为空）")

        media_id = str(media_ids[0])
        media_asset: Optional[MediaAsset] = await db.get(MediaAsset, media_id)
        if media_asset is None:
            raise ValueError(f"媒体资产不存在: {media_id}")

        # 从 MinIO 下载视频
        local_path = self.work_dir / f"{media_id[:8]}_{media_asset.original_filename}"
        self.minio.fget_object(MINIO_BUCKET, media_asset.storage_path, str(local_path))
        logger.info(f"Downloaded {media_asset.storage_path} -> {local_path}")

        # 1. 构建任务上下文
        task_context = await self._build_task_context(db, job, media_asset, local_path)
        logger.info(f"Task context: task_type={task_context.task_type}, quality={task_context.quality_requirement}")

        # 2. 资产发现
        asset_status = self.asset_discovery.discover(
            project_id=str(job.project_id) if job.project_id else f"job_{job.id}",
            media_id=media_id
        )
        logger.info(f"Asset discovery: subtitle={asset_status.subtitle_state}, character_db={asset_status.character_db_state}")

        # 3. 构建能力矩阵（from_asset_status 是 CapabilityBuilder 的实例方法）
        capability_matrix_builder = CapabilityBuilder()
        capability_matrix = capability_matrix_builder.from_asset_status(asset_status)
        logger.info(f"Capability matrix: production_ready={capability_matrix.is_ready_for_production()}")

        # 4. 选择工作流
        selection = self.workflow_selector.select(task_context, capability_matrix)
        logger.info(f"Selected workflow: {selection.workflow_type.value} - {selection.reason}")

        # 5. 生成执行计划
        execution_plan = self.workflow_planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=selection.workflow_type,
            existing_artifacts=asset_status.artifacts,
            failed_module=job.config.get("failed_module") if job.config else None
        )
        logger.info(f"Execution plan: {len(execution_plan.steps)} steps, estimated {execution_plan.total_estimated_duration}s")

        # 保存执行计划到 job config
        if not job.config:
            job.config = {}
        job.config["execution_plan"] = execution_plan.model_dump()
        await db.commit()

        # 6. 执行计划
        return await self._execute_plan(db, job, execution_plan, local_path)

    async def _build_task_context(
        self, 
        db, 
        job: Job, 
        media_asset: MediaAsset, 
        video_path: Path
    ) -> TaskContext:
        """构建任务上下文"""
        # 从 job.config 获取配置，或使用默认值
        job_config = job.config or {}
        
        # 解析任务类型
        task_type_str = job_config.get("task_type", "episode")
        try:
            task_type = TaskType(task_type_str)
        except ValueError:
            task_type = TaskType.EPISODE
        
        # 解析质量要求
        quality_str = job_config.get("quality_requirement", "standard")
        try:
            quality_requirement = QualityRequirement(quality_str)
        except ValueError:
            quality_requirement = QualityRequirement.STANDARD
        
        # 获取视频时长
        duration_seconds = None
        try:
            probe_data = self.ffprobe.probe(video_path)
            duration_seconds = self.ffprobe.get_duration(probe_data)
        except Exception as e:
            logger.warning(f"Failed to get video duration: {e}")
        
        # 构建任务上下文
        return TaskContext(
            project_id=str(job.project_id) if job.project_id else f"job_{job.id}",
            media_id=str(media_asset.id),
            task_type=task_type,
            duration_seconds=duration_seconds,
            quality_requirement=quality_requirement,
            force_workflow=job_config.get("force_workflow"),
            first_processing=job_config.get("first_processing", True),
        )

    async def _execute_plan(
        self,
        db,
        job: Job,
        execution_plan,
        video_path: Path
    ) -> dict:
        """执行执行计划
        
        根据 ExecutionPlan 中的步骤执行模块，支持 LOAD/SKIP/RUN_INCREMENTAL/RUN_FULL
        """
        project_id = str(job.project_id) if job.project_id else f"job_{job.id}"
        work_dir = self.work_dir / f"job_{job.id}"
        work_dir.mkdir(parents=True, exist_ok=True)

        # 创建完整流水线执行器
        executor = FullPipelineExecutor(
            project_id=project_id,
            video_path=video_path,
            work_dir=work_dir
        )

        # 执行计划中的步骤
        completed_modules = set()
        failed_modules = []
        total_steps = len(execution_plan.steps)

        for i, step in enumerate(execution_plan.steps):
            # 计算进度
            progress = int(i / total_steps * 100)
            module = step.module
            mode = step.mode
            
            # 发送开始进度
            await self._broadcast_progress(
                job,
                progress,
                module,
                f"[{mode.value.upper()}] {MODULE_STAGE_MAP.get(module, f'正在处理 {module}')}"
            )

            try:
                if mode == ExecutionMode.SKIP:
                    # 跳过模块
                    logger.info(f"Skipping {module}: {step.reason}")
                    completed_modules.add(module)
                    
                elif mode == ExecutionMode.LOAD:
                    # 加载已有 Artifact
                    logger.info(f"Loading {module}: {step.reason}")
                    # 加载逻辑：标记为已完成，跳过实际执行
                    # 实际的 Artifact 数据由 AssetDiscovery 已发现
                    completed_modules.add(module)
                    
                elif mode in [ExecutionMode.RUN_FULL, ExecutionMode.RUN_INCREMENTAL]:
                    # 执行模块
                    logger.info(f"Executing {module} ({mode.value}): {step.reason}")
                    await getattr(executor, f"exec_{module}")()
                    completed_modules.add(module)
                
                # 发送完成进度
                await self._broadcast_progress(
                    job,
                    int((i + 1) / total_steps * 100),
                    module,
                    f"{MODULE_STAGE_MAP.get(module, module)} 完成 ({mode.value})"
                )
                
            except Exception as e:
                error_msg = ERROR_MESSAGE_MAP.get(module, f"{module} 执行失败: {str(e)}")
                logger.error(f"Module {module} failed: {e}")
                failed_modules.append((module, str(e)))
                
                # 记录失败模块到 job.config（用于断点续跑）
                if not job.config:
                    job.config = {}
                job.config["failed_module"] = module
                await db.commit()
                
                # 发送失败进度
                await self._broadcast_progress(job, progress, module, error_msg)
                break

        # 如果有失败模块，抛出异常
        if failed_modules:
            failed_info = ", ".join([f"{m}: {e}" for m, e in failed_modules])
            raise RuntimeError(f"流水线执行失败: {failed_info}")

        # 发送完成进度
        await self._broadcast_progress(job, 100, "DONE", "处理完成")

        # 从执行器上下文读取 M13 QA 评分
        qa_score = None
        m13 = getattr(executor, "ctx", {}).get("M13")
        if m13:
            m13_result = m13.get("result")
            if isinstance(m13_result, dict):
                qa_score = m13_result.get("overall_score")

        return {
            "completed_modules": len(completed_modules),
            "total_steps": total_steps,
            "work_dir": str(work_dir),
            "qa_score": qa_score,
        }

    # ------------------------------------------------------------------
    # 完整流水线执行（保留用于向后兼容）
    # ------------------------------------------------------------------
    async def _run_full_pipeline(self, db, job: Job) -> dict:
        """
        执行完整 M01~M14 流水线

        从 input_artifacts 解析媒体资产 → MinIO 下载 → 执行完整流水线 → 产出 final 视频
        """
        media_ids = job.input_artifacts or []
        if not media_ids:
            raise ValueError("任务无输入媒体（input_artifacts 为空）")

        media_id = str(media_ids[0])
        media_asset: Optional[MediaAsset] = await db.get(MediaAsset, media_id)
        if media_asset is None:
            raise ValueError(f"媒体资产不存在: {media_id}")

        # 从 MinIO 下载视频
        local_path = self.work_dir / f"{media_id[:8]}_{media_asset.original_filename}"
        self.minio.fget_object(MINIO_BUCKET, media_asset.storage_path, str(local_path))
        logger.info(f"Downloaded {media_asset.storage_path} -> {local_path}")

        # 创建完整流水线执行器
        executor = FullPipelineExecutor(
            project_id=str(job.project_id) if job.project_id else f"job_{job.id}",
            video_path=local_path,
            work_dir=self.work_dir / f"job_{job.id}"
        )

        # 发送初始进度
        await self._broadcast_progress(job, 0, "M01", "准备开始处理")

        # 执行完整流水线并监听进度
        total_modules = 14
        completed = 0
        failed_modules = []

        # 逐模块执行，发送进度
        for mod in ["M01", "M02", "M03", "M05", "M04", "M06", "M07",
                    "M08", "M09", "M10", "M11", "M12", "M13", "M14"]:
            # 发送模块开始进度
            await self._broadcast_progress(
                job,
                int(completed / total_modules * 100),
                mod,
                MODULE_STAGE_MAP.get(mod, f"正在执行 {mod}")
            )

            try:
                await getattr(executor, f"exec_{mod}")()
                completed += 1
                # 发送模块完成进度
                await self._broadcast_progress(
                    job,
                    int(completed / total_modules * 100),
                    mod,
                    f"{MODULE_STAGE_MAP.get(mod, mod)} 完成"
                )
            except Exception as e:
                error_msg = ERROR_MESSAGE_MAP.get(mod, f"{mod} 执行失败: {str(e)}")
                logger.error(f"Module {mod} failed: {e}")
                failed_modules.append((mod, str(e)))
                # 发送失败进度
                await self._broadcast_progress(job, int(completed / total_modules * 100), mod, error_msg)
                break

        logger.info(f"Full pipeline completed: {completed}/{total_modules} modules, failed: {failed_modules}")

        # 如果有失败模块，抛出异常
        if failed_modules:
            failed_info = ", ".join([f"{m}: {e}" for m, e in failed_modules])
            raise RuntimeError(f"流水线执行失败: {failed_info}")

        # 发送完成进度
        await self._broadcast_progress(job, 100, "DONE", "处理完成")

        return {
            "completed_modules": completed,
            "total_modules": total_modules,
            "failed_modules": failed_modules
        }

    async def _broadcast_progress(
        self,
        job: Job,
        progress: int,
        module: str,
        message: str
    ):
        """广播作业进度到 WebSocket"""
        try:
            from filmdub.apps.api.websocket.handler import broadcast_job_progress
            project_id = str(job.project_id) if job.project_id else "unknown"
            await broadcast_job_progress(
                job_id=str(job.id),
                project_id=project_id,
                progress=float(progress),
                status="running",
                message=message
            )
        except Exception as e:
            logger.warning(f"Failed to broadcast progress: {e}")


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    poll_interval = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    runner = JobRunner(poll_interval=poll_interval)
    try:
        await runner.run()
    except KeyboardInterrupt:
        logger.info("Job Runner stopped")


if __name__ == "__main__":
    asyncio.run(main())
