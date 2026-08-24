"""
M11 Video Assembly Worker

视频组装与最终编码 Worker
"""
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

from filmdub.workers.common import save_json_artifact, run_worker_loop
from filmdub.orchestrator.job_logs import job_log_store

from .config import M11Config
from .assembler import VideoAssembler
from .models import AudioSegment, SubtitleEntry, AudioTrack, AudioTrackType


class M11Worker:
    """M11 Worker"""

    def __init__(self, config: M11Config = None, projects_base_dir: str | Path = "./artifacts"):
        """
        初始化 Worker

        Args:
            config: M11 配置
            projects_base_dir: 项目基目录（用于读写 Artifact）
        """
        self.config = config or M11Config()
        self.projects_base_dir = Path(projects_base_dir)
        self.assembler = VideoAssembler(self.config)

    def _progress_callback(self, job_id: str, project_id: str):
        """构造进度回调：把组装进度写入作业日志存储（Layer 0 可查询）。"""
        def _report(progress: float) -> None:
            logger.info(f"Assembly progress [{project_id}/{job_id}]: {progress * 100:.1f}%")
            job_log_store.append(
                job_id,
                "progress",
                f"视频组装进度 {progress * 100:.1f}%",
                {"project_id": project_id, "progress": progress},
            )
        return _report

    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理作业

        Args:
            job_data: 作业数据

        Returns:
            处理结果
        """
        job_id = job_data.get("job_id")
        project_id = job_data.get("project_id", "")

        logger.info(f"Processing job {job_id} for project {project_id}")

        try:
            # 1. 获取输入数据
            source_video_path = job_data.get("source_video_path")
            output_path = job_data.get("output_path")
            audio_segments_data = job_data.get("audio_segments", [])
            subtitles_data = job_data.get("subtitles", [])

            if not source_video_path or not output_path:
                raise ValueError("Missing source_video_path or output_path in job data")

            if not Path(source_video_path).exists():
                raise FileNotFoundError(f"Source video not found: {source_video_path}")

            # 2. 转换数据
            audio_segments = [
                AudioSegment(**seg)
                for seg in audio_segments_data
            ]

            subtitles = [
                SubtitleEntry(**sub)
                for sub in subtitles_data
            ]

            # 3. 组装视频（进度写入作业日志）
            result = await self.assembler.assemble_video(
                source_video_path=source_video_path,
                audio_segments=audio_segments,
                output_path=output_path,
                subtitles=subtitles,
                project_id=project_id,
                progress_callback=self._progress_callback(job_id, project_id)
            )

            # 4. 构建响应并持久化结果 Artifact
            response = {
                "status": "success",
                "result": result.to_dict(),
            }
            response["artifact_path"] = save_json_artifact(
                project_id,
                "final_video",
                response,
                self.projects_base_dir,
            )

            job_log_store.append(
                job_id,
                "completed",
                f"视频组装完成：{result.video_path}",
                {"project_id": project_id, "result": result.to_dict()},
            )

            logger.info(f"Job {job_id} completed successfully")

            return response

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            job_log_store.append(
                job_id,
                "error",
                f"视频组装失败: {e}",
                {"project_id": project_id},
            )
            return {
                "status": "error",
                "error": str(e)
            }


async def main():
    """主函数：运行文件系统作业轮询循环。"""
    logger.info("M11 Video Assembly Worker starting...")

    worker = M11Worker()
    await run_worker_loop(
        "M11",
        worker.process_job,
        Path("./queue/m11"),
    )


if __name__ == "__main__":
    asyncio.run(main())
