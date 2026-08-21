"""
M11 Video Assembly Worker

视频组装 Worker
"""
import asyncio
import sys
from pathlib import Path
from typing import Any, Dict
from loguru import logger

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .config import M11Config
from .assembler import VideoAssembler


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
            input_video_path = job_data.get("input_video_path")
            audio_artifacts = job_data.get("audio_artifacts")
            output_video_path = job_data.get("output_video_path")
            subtitles = job_data.get("subtitles")

            if not input_video_path:
                raise ValueError("Missing input_video_path in job data")

            if not audio_artifacts:
                raise ValueError("Missing audio_artifacts in job data")

            if not output_video_path:
                # 生成默认输出路径
                output_video_path = str(
                    Path("./output") / project_id / "final_video.mp4"
                )

            # 确保输出目录存在
            Path(output_video_path).parent.mkdir(parents=True, exist_ok=True)

            # 2. 在线程池中运行组装（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.assembler.assemble_video,
                input_video_path,
                audio_artifacts,
                output_video_path,
                subtitles
            )

            # 3. 构建返回结果
            response = {
                "status": result.status,
                "job_id": job_id,
                "project_id": project_id
            }

            if result.status == "success":
                response.update({
                    "video_artifact": result.video_artifact.to_dict(),
                    "output_path": result.video_artifact.file_path
                })
            else:
                response["error"] = result.error

            # 4. 保存 Artifact
            # TODO: 保存到 Artifact Registry

            logger.info(f"Job {job_id} completed with status: {result.status}")

            return response

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            return {
                "status": "error",
                "job_id": job_id,
                "project_id": project_id,
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
