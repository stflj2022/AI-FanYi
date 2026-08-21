"""
M06 Speaker Mapping Worker

说话人到人物映射 Worker
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

from .config import M06Config
from .mapper import SpeakerToCharacterMapper
from .voice_assigner import VoiceProfileAssigner
from .models import MappingResult


class M06Worker:
    """M06 Worker"""

    def __init__(self, config: M06Config = None):
        """
        初始化 Worker

        Args:
            config: M06 配置
        """
        self.config = config or M06Config()
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

            # 5. 保存 Artifact
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
    logger.info("M06 Speaker Mapping Worker starting...")

    # 创建 Worker
    worker = M06Worker()

    # TODO: 实现 Worker 通信循环
    # 这里应该：
    # 1. 注册到 Layer 0
    # 2. 接收作业
    # 3. 发送心跳
    # 4. 处理作业

    logger.info("M06 Speaker Mapping Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
