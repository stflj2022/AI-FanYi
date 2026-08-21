"""
M08 Prosody Planning Worker

韵律规划 Worker
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

import logging

logger = logging.getLogger(__name__)

from filmdub.workers.common import save_json_artifact, run_worker_loop

from .config import M08Config
from .planner import ProsodyPlanner


class M08Worker:
    """M08 Worker"""

    def __init__(self, config: M08Config = None, projects_base_dir: str | Path = "./artifacts"):
        """
        初始化 Worker

        Args:
            config: M08 配置
            projects_base_dir: 项目基目录（用于读写 Artifact）
        """
        self.config = config or M08Config()
        self.projects_base_dir = Path(projects_base_dir)
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

            # 4. 持久化结果 Artifact
            result["artifact_path"] = save_json_artifact(
                project_id,
                "prosody",
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
    logger.info("M08 Prosody Planning Worker starting...")

    worker = M08Worker()
    await run_worker_loop(
        "M08",
        worker.process_job,
        Path("./queue/m08"),
    )


if __name__ == "__main__":
    asyncio.run(main())
