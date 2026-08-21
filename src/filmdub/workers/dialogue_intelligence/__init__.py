"""
M07 Dialogue Intelligence Worker

对白智能处理 Worker
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

import logging

logger = logging.getLogger(__name__)

from filmdub.workers.common import save_json_artifact, run_worker_loop

from .config import M07Config
from .processor import DialogueIntelligence


class M07Worker:
    """M07 Worker"""

    def __init__(self, config: M07Config = None, projects_base_dir: str | Path = "./artifacts"):
        """
        初始化 Worker

        Args:
            config: M07 配置
            projects_base_dir: 项目基目录（用于读写 Artifact）
        """
        self.config = config or M07Config()
        self.projects_base_dir = Path(projects_base_dir)
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

            # 4. 持久化结果 Artifact
            result["artifact_path"] = save_json_artifact(
                project_id,
                "dialogue_intelligence",
                result,
                self.projects_base_dir
            )

            logger.info(f"Job {job_id} completed successfully")

            return result

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


async def main():
    """主函数：运行文件系统作业轮询循环。"""
    logger.info("M07 Dialogue Intelligence Worker starting...")

    worker = M07Worker()
    await run_worker_loop(
        "M07",
        worker.process_job,
        Path("./queue/m07"),
    )


if __name__ == "__main__":
    asyncio.run(main())
