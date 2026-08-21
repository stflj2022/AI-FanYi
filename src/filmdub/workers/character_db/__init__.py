"""
M04 Character Database Worker

人物数据库构建 Worker
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

import logging

logger = logging.getLogger(__name__)

from filmdub.workers.common import save_json_artifact, run_worker_loop

from .config import M04Config
from .clustering import SpeakerClustering
from .linker import CharacterLinker
from .models import Cluster, SpeakerEmbedding, Character


class M04Worker:
    """M04 Worker"""

    def __init__(self, config: M04Config = None, projects_base_dir: str | Path = "./artifacts"):
        """
        初始化 Worker

        Args:
            config: M04 配置
            projects_base_dir: 项目基目录（用于读写 Artifact）
        """
        self.config = config or M04Config()
        self.projects_base_dir = Path(projects_base_dir)
        self.clustering = SpeakerClustering(
            eps=self.config.clustering_eps,
            min_samples=self.config.clustering_min_samples
        )
        self.linker = CharacterLinker(self.config)

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
            # 1. 获取输入 Artifact（说话人嵌入）
            embeddings = await self._load_speaker_embeddings(
                project_id,
                job_data.get("input_artifact_id")
            )

            if not embeddings:
                raise ValueError("No speaker embeddings found in input artifact")

            logger.info(f"Loaded {len(embeddings)} speaker embeddings")

            # 2. 聚类
            clusters = self.clustering.cluster_speakers(embeddings)

            if not clusters:
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

            # 5. 构建结果
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

            # 6. 持久化结果 Artifact
            result["artifact_path"] = save_json_artifact(
                project_id,
                "character_db",
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

    async def _load_speaker_embeddings(
        self,
        project_id: str,
        input_artifact_id: Optional[str] = None
    ) -> List[SpeakerEmbedding]:
        """
        从项目 Artifact 目录加载说话人嵌入。

        Args:
            project_id: 项目 ID
            input_artifact_id: 输入 Artifact 名称（可选）

        Returns:
            说话人嵌入列表

        Raises:
            FileNotFoundError: 输入 Artifact 不存在
        """
        artifact_dir = self.projects_base_dir / project_id / "artifacts"

        # 优先使用显式指定的 artifact，否则回退到约定文件名
        if input_artifact_id:
            candidate = artifact_dir / f"{input_artifact_id}.json"
        else:
            candidate = artifact_dir / "speaker_embeddings.json"

        if not candidate.exists():
            raise FileNotFoundError(f"Speaker embeddings artifact not found: {candidate}")

        raw = json.loads(candidate.read_text(encoding="utf-8"))

        # 兼容两种结构：直接列表，或 {"embeddings": [...]}
        items = raw if isinstance(raw, list) else raw.get("embeddings", raw.get("segments", []))

        embeddings = [
            SpeakerEmbedding(
                segment_id=item["segment_id"],
                start_time=float(item["start_time"]),
                end_time=float(item["end_time"]),
                embedding=[float(x) for x in item["embedding"]],
                confidence=float(item.get("confidence", 0.0)),
                text=item.get("text", "")
            )
            for item in items
        ]

        return embeddings

    def _get_cluster_labels(
        self,
        embeddings: List[SpeakerEmbedding],
        clusters: List[Cluster]
    ) -> List[int]:
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

        # 转换为 numpy 数组，保证下游 numpy 布尔索引/evaluate_clustering 正确工作
        return np.array(labels, dtype=int)


async def main():
    """主函数：运行文件系统作业轮询循环。"""
    logger.info("M04 Character Database Worker starting...")

    worker = M04Worker()
    await run_worker_loop(
        "M04",
        worker.process_job,
        Path("./queue/m04"),
    )


if __name__ == "__main__":
    asyncio.run(main())
