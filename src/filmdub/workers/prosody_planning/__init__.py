"""
M08 Prosody Planning Worker

韵律规划 Worker
"""
import asyncio
import sys
import os
import json
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .config import M08Config
from .planner import ProsodyPlanner


class M08Worker:
    """M08 Worker"""

    def __init__(self, config: M08Config = None):
        """
        初始化 Worker

        Args:
            config: M08 配置
        """
        self.config = config or M08Config()
        self.planner = ProsodyPlanner(self.config)

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
            dialogues = job_data.get("dialogues", [])
            voice_profiles = job_data.get("voice_profiles", [])
            audio_features = job_data.get("audio_features")

            if not dialogues or not voice_profiles:
                raise ValueError("Missing dialogues or voice_profiles in job data")

            # 2. 规划韵律
            prepared_dialogues = await self.planner.plan_dialogues(
                dialogues,
                voice_profiles,
                audio_features
            )

            # 3. 构建结果
            result = {
                "status": "success",
                "prepared_dialogues": [
                    d.to_dict() for d in prepared_dialogues
                ],
                "total": len(prepared_dialogues)
            }

            # 4. 保存 Artifact
            # TODO: 保存到 Artifact Registry

            logger.info(f"Job {job_id} completed successfully")

            return result

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


async def main():
    """主函数"""
    logger.info("M08 Prosody Planning Worker starting...")

    # 创建 Worker
    worker = M08Worker()

    # TODO: 实现 Worker 通信循环

    logger.info("M08 Prosody Planning Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
