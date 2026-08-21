"""
M07 Dialogue Intelligence Worker

对白智能处理 Worker
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

from .config import M07Config
from .processor import DialogueIntelligence


class M07Worker:
    """M07 Worker"""

    def __init__(self, config: M07Config = None):
        """
        初始化 Worker

        Args:
            config: M07 配置
        """
        self.config = config or M07Config()
        self.processor = DialogueIntelligence(self.config)

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
            characters = job_data.get("characters", [])
            context = job_data.get("context", {})

            if not dialogues:
                raise ValueError("Missing dialogues in job data")

            # 2. 处理对白
            processed_dialogues = await self.processor.process_dialogues(
                dialogues,
                characters,
                context
            )

            # 3. 构建结果
            result = {
                "status": "success",
                "processed_dialogues": [
                    d.to_dict() for d in processed_dialogues
                ],
                "total": len(processed_dialogues),
                "needs_review": sum(1 for d in processed_dialogues if d.needs_manual_review)
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
    logger.info("M07 Dialogue Intelligence Worker starting...")

    # 创建 Worker
    worker = M07Worker()

    # TODO: 实现 Worker 通信循环

    logger.info("M07 Dialogue Intelligence Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
