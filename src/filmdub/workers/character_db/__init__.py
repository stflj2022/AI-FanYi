"""
M04 Character Database Worker

人物数据库构建 Worker
"""
import asyncio
import sys
import os
import uuid
import json
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .config import M04Config
from .clustering import SpeakerClustering
from .linker import CharacterLinker
from .models import SpeakerEmbedding, Character
from orchestrator.artifact_registry import ArtifactRegistry
from orchestrator.storage import LocalStorage


class M04Worker:
    """M04 Worker"""

    def __init__(self, config: M04Config = None):
        """
        初始化 Worker

        Args:
            config: M04 配置
        """
        self.config = config or M04Config()
        self.clustering = SpeakerClustering(
            eps=self.config.clustering_eps,
            min_samples=self.config.clustering_min_samples
        )
        self.linker = CharacterLinker(self.config)

        # TODO: 从环境变量获取配置
        self.artifact_registry = None
        self.storage = None

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
            # 1. 获取输入 Artifact
            input_artifact_id = job_data.get("input_artifact_id")
            embeddings = await self._load_speaker_embeddings(input_artifact_id)

            if not embeddings:
                raise ValueError("No speaker embeddings found")

            logger.info(f"Loaded {len(embeddings)} speaker embeddings")

            # 2. 聚类
            clusters = self.clustering.cluster_speakers(embeddings)

            if not clusters:
                logger.warning("No clusters found")
                return {
                    "status": "success",
                    "characters": [],
                    "clusters": []
                }

            # 3. 评估聚类
            labels = self._get_cluster_labels(embeddings, clusters)
            metrics = self.clustering.evaluate_clustering(embeddings, labels)

            # 4. 链接到人物
            characters = self.linker.link_speakers_to_characters(
                clusters,
                project_id
            )

            # 5. 保存结果
            result = {
                "status": "success",
                "characters": [c.to_dict() for c in characters],
                "clusters": [
                    {
                        "cluster_id": c.cluster_id,
                        "size": c.size,
                        "speaker_count": len(c.speaker_embeddings)
                    }
                    for c in clusters
                ],
                "metrics": metrics
            }

            # 6. 保存 Artifact
            # TODO: 保存到 Artifact Registry

            logger.info(f"Job {job_id} completed successfully")

            return result

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def _load_speaker_embeddings(
        self,
        artifact_id: str
    ) -> list[SpeakerEmbedding]:
        """
        加载说话人嵌入

        Args:
            artifact_id: Artifact ID

        Returns:
            说话人嵌入列表
        """
        # TODO: 从 Artifact Registry 加载
        # 临时实现：返回模拟数据
        return []

    def _get_cluster_labels(
        self,
        embeddings: List[SpeakerEmbedding],
        clusters: list[Cluster]
    ) -> list[int]:
        """
        获取聚类标签

        Args:
            embeddings: 说话人嵌入列表
            clusters: 聚类列表

        Returns:
            标签列表
        """
        # 创建嵌入到聚类的映射
        cluster_map = {}
        for cluster in clusters:
            for se in cluster.speaker_embeddings:
                cluster_map[se.segment_id] = cluster.cluster_id

        # 生成标签
        labels = [
            cluster_map.get(se.segment_id, -1)
            for se in embeddings
        ]

        return labels


async def main():
    """主函数"""
    logger.info("M04 Character Database Worker starting...")

    # 创建 Worker
    worker = M04Worker()

    # TODO: 实现 Worker 通信循环
    # 这里应该：
    # 1. 注册到 Layer 0
    # 2. 接收作业
    # 3. 发送心跳
    # 4. 处理作业

    logger.info("M04 Character Database Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
