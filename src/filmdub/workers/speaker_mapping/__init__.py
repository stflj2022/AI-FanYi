"""
M06 Speaker Mapping Worker

说话人到人物映射 Worker
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

import logging

logger = logging.getLogger(__name__)

from filmdub.workers.common import save_json_artifact, run_worker_loop

from .config import M06Config
from .mapper import SpeakerToCharacterMapper
from .voice_assigner import VoiceProfileAssigner
from .models import MappingResult


class M06Worker:
    """M06 Worker"""

    def __init__(self, config: M06Config = None, projects_base_dir: str | Path = "./artifacts"):
        """
        初始化 Worker

        Args:
            config: M06 配置
            projects_base_dir: 项目基目录（用于读写 Artifact）
        """
        self.config = config or M06Config()
        self.projects_base_dir = Path(projects_base_dir)
        self.mapper = SpeakerToCharacterMapper(self.config)
        self.voice_assigner = VoiceProfileAssigner(self.config)

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
            speakers = job_data.get("speakers", [])
            characters = job_data.get("characters", [])
            existing_mappings = job_data.get("existing_mappings", [])
            existing_voice_profiles = job_data.get("existing_voice_profiles", [])

            if not speakers or not characters:
                raise ValueError("Missing speakers or characters in job data")

            # 2. 执行映射
            mapping_result = await self.mapper.map_speakers(
                speakers,
                characters,
                existing_mappings,
                job_data.get("project_metadata")
            )

            # 3. 分配音色
            voice_profiles = await self.voice_assigner.assign_voice_profiles(
                mapping_result.mappings,
                characters,
                existing_voice_profiles,
                job_data.get("audio_paths")
            )

            mapping_result.voice_profiles = voice_profiles

            # 4. 构建结果
            result = {
                "status": "success",
                "mapping": mapping_result.to_dict()
            }

            # 5. 持久化结果 Artifact
            result["artifact_path"] = save_json_artifact(
                project_id,
                "speaker_mapping",
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
    logger.info("M06 Speaker Mapping Worker starting...")

    worker = M06Worker()
    await run_worker_loop(
        "M06",
        worker.process_job,
        Path("./queue/m06"),
    )


if __name__ == "__main__":
    asyncio.run(main())
