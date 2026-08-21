"""
M09 Voice Synthesis Worker

语音合成 Worker
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List

import logging

logger = logging.getLogger(__name__)

from filmdub.workers.common import save_json_artifact, run_worker_loop

from .config import M09Config
from .model_manager import TTSModelManager
from .batch_synthesizer import BatchSynthesizer
from .models import M09Input


class M09Worker:
    """M09 Worker"""

    def __init__(self, config: M09Config = None, projects_base_dir: str | Path = "./artifacts"):
        """
        初始化 Worker

        Args:
            config: M09 配置
            projects_base_dir: 项目基目录（用于读写 Artifact）
        """
        self.config = config or M09Config()
        self.projects_base_dir = Path(projects_base_dir)
        self.model_manager = TTSModelManager(self.config)
        self.batch_synthesizer = BatchSynthesizer(self.model_manager, self.config)

        # 加载默认模型（失败时记录警告，Worker 仍可启动）
        loaded = self.model_manager.load_model(self.config.default_model)
        if not loaded:
            logger.warning(
                f"Default model '{self.config.default_model}' failed to load; "
                "synthesis jobs will return errors until a model is available."
            )

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
            prepared_dialogues = job_data.get("prepared_dialogues")
            output_dir = job_data.get("output_dir", f"./output/{project_id}")

            if not prepared_dialogues:
                raise ValueError("Missing prepared_dialogues in job data")

            # 2. 转换为 M09Input
            inputs = self._convert_to_inputs(prepared_dialogues)

            # 3. 批量合成
            outputs = await self.batch_synthesizer.synthesize_batch(
                inputs,
                output_dir
            )

            # 4. 构建结果
            result = {
                "status": "success",
                "outputs": [o.to_dict() for o in outputs],
                "num_success": sum(1 for o in outputs if o.status == "success"),
                "num_error": sum(1 for o in outputs if o.status == "error"),
                "output_dir": output_dir
            }

            # 5. 持久化结果 Artifact
            result["artifact_path"] = save_json_artifact(
                project_id,
                "synthesis",
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

    def _convert_to_inputs(
        self,
        prepared_dialogues: List[Dict[str, Any]]
    ) -> List[M09Input]:
        """
        转换为 M09Input

        Args:
            prepared_dialogues: 准备好的对白列表

        Returns:
            M09Input 列表
        """
        inputs = []

        for dialogue in prepared_dialogues:
            prosody = dialogue.get("prosody", {})

            input_item = M09Input(
                dialogue_id=dialogue.get("dialogue_id"),
                character_id=dialogue.get("character_id"),
                voice_profile_id=dialogue.get("voice_profile_id", "default"),
                text=dialogue.get("text"),
                speed=prosody.get("speed", 1.0),
                pitch=prosody.get("pitch", 0.0),
                pause_before=prosody.get("pause_before", 0.0),
                pause_after=prosody.get("pause_after", 0.0),
                energy=prosody.get("energy", 1.0),
                emotion=prosody.get("emotion", "neutral"),
                emotion_intensity=prosody.get("emotion_intensity", 0.5),
                metadata=dialogue.get("metadata")
            )

            inputs.append(input_item)

        return inputs


async def main():
    """主函数：运行文件系统作业轮询循环。"""
    logger.info("M09 Voice Synthesis Worker starting...")

    worker = M09Worker()
    await run_worker_loop(
        "M09",
        worker.process_job,
        Path("./queue/m09"),
    )


if __name__ == "__main__":
    asyncio.run(main())
