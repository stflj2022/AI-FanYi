"""
M11 Video Assembly Worker

视频组装与最终编码 Worker
"""
import asyncio
import sys
import os
import json
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .config import M11Config
from .assembler import VideoAssembler
from .models import AudioSegment, SubtitleEntry


class M11Worker:
    """M11 Worker"""

    def __init__(self, config: M11Config = None):
        """
        初始化 Worker

        Args:
            config: M11 配置
        """
        self.config = config or M11Config()
        self.assembler = VideoAssembler(self.config)

    async def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理作业

        Args:
            job_data: 作业数据

        Returns:
            处理结果
        """
        job_id = job_data.get("job_id")
        project_id = job_data.get("project_id")

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

            # 3. 进度回调
            async def progress_callback(progress: float):
                logger.info(f"Assembly progress: {progress * 100:.1f}%")
                # TODO: 向 Layer 0 报告进度

            # 4. 组装视频
            result = await self.assembler.assemble_video(
                source_video_path=source_video_path,
                audio_segments=audio_segments,
                output_path=output_path,
                subtitles=subtitles,
                progress_callback=progress_callback
            )

            # 5. 构建响应
            response = {
                "status": "success",
                "result": result.to_dict()
            }

            # 6. 保存 Artifact
            # TODO: 保存到 Artifact Registry

            logger.info(f"Job {job_id} completed successfully")

            return response

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


async def main():
    """主函数"""
    logger.info("M11 Video Assembly Worker starting...")

    # 创建 Worker
    worker = M11Worker()

    # TODO: 实现 Worker 通信循环

    logger.info("M11 Video Assembly Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
