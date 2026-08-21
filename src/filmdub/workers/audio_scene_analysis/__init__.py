"""
M05 Audio & Scene Analysis Worker

音频与场景分析 Worker
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

import logging

logger = logging.getLogger(__name__)

from filmdub.workers.common import save_json_artifact, run_worker_loop

from .config import M05Config
from .diarization import SpeakerDiarization
from .embedding import SpeakerEmbeddingExtractor
from .audio_features import AudioFeatureExtractor
from .models import DiarizationResult, SpeakerEmbedding, AudioFeatures


class M05Worker:
    """M05 Worker"""

    def __init__(self, config: M05Config = None, projects_base_dir: str | Path = "./artifacts"):
        """
        初始化 Worker

        Args:
            config: M05 配置
            projects_base_dir: 项目基目录（用于读写 Artifact）
        """
        self.config = config or M05Config()
        self.projects_base_dir = Path(projects_base_dir)
        self.diarization = SpeakerDiarization(self.config)
        self.embedding_extractor = SpeakerEmbeddingExtractor(self.config)
        self.feature_extractor = AudioFeatureExtractor(self.config)

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
            # 1. 获取音频路径
            audio_path = job_data.get("audio_path")

            if not audio_path:
                raise ValueError("Missing audio_path in job data")

            if not Path(audio_path).exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # 2. 说话人分离
            num_speakers = job_data.get("num_speakers")
            diarization_result = self.diarization.diarize(audio_path, num_speakers)

            # 3. 过滤短片段
            diarization_result = self.diarization.filter_short_segments(
                diarization_result
            )

            # 4. 提取说话人嵌入
            embeddings = self.embedding_extractor.extract(
                audio_path,
                diarization_result.segments
            )

            # 5. 提取音频特征
            features = self.feature_extractor.extract(
                audio_path,
                diarization_result.segments
            )

            # 6. 构建结果
            result = {
                "status": "success",
                "diarization": diarization_result.to_dict(),
                "embeddings": [
                    {
                        "speaker_id": e.speaker_id,
                        "start_time": e.start_time,
                        "end_time": e.end_time,
                        "embedding": e.embedding,
                        "confidence": e.confidence,
                        "segment_count": e.segment_count
                    }
                    for e in embeddings
                ],
                "features": [f.to_dict() for f in features]
            }

            # 7. 持久化结果 Artifact
            result["artifact_path"] = save_json_artifact(
                project_id,
                "audio_analysis",
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
    logger.info("M05 Audio & Scene Analysis Worker starting...")

    worker = M05Worker()
    await run_worker_loop(
        "M05",
        worker.process_job,
        Path("./queue/m05"),
    )


if __name__ == "__main__":
    asyncio.run(main())
