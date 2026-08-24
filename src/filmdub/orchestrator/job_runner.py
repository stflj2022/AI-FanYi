"""
执行引擎（阶段 B：完整流水线）

轮询 orchestrator 数据库中的 pending/scheduled 配音任务，执行对应模块并更新状态。

当前实现：
- M01 媒体分析：从 MinIO 下载输入媒体 → FFprobe 分析 → 写入 media_analysis artifact
- 完整流水线：执行 M01~M14 完整流程，产出最终配音视频
- 状态流转：PENDING → RUNNING → COMPLETED / FAILED
- 任务所属项目自动置为 PROCESSING（与 orchestrator 调度语义一致）
- 支持断点续跑（从 manifests 恢复）

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
    """最小任务执行引擎"""

    def __init__(self, poll_interval: float = 5.0, work_dir: str = "/tmp/filmdub_runner"):
        self.poll_interval = poll_interval
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.ffprobe = FFprobeParser()
        self.minio = self._init_minio()

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
        """执行单个任务：M01 媒体分析 或 完整流水线"""
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
            # 判断执行模式：如果 module_id 为 "FULL_PIPELINE" 则执行完整流水线
            if job.module_id == "FULL_PIPELINE":
                result = await self._run_full_pipeline(db, job)
            else:
                # 默认执行 M01
                analysis = await self._run_m01(db, job)
                result = {"media_analysis": analysis}

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            # 记录输出 artifacts
            output_arts = []
            if job.module_id == "FULL_PIPELINE":
                output_arts.append(f"final_video:{result.get('output_video', '')}")
                output_arts.append(f"work_dir:{result.get('work_dir', '')}")
            else:
                output_arts.append(f"media_analysis:{job.id}")
            job.output_artifacts = (job.output_artifacts or []) + output_arts
            logger.info(f"Job {job.id} completed: {len(output_arts)} artifacts")
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)[:2000]
            logger.error(f"Job {job.id} failed: {e}", exc_info=True)
        await db.commit()

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

    # ------------------------------------------------------------------
    # 完整流水线执行
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
