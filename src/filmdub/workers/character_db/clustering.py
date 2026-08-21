"""
说话人聚类模块

使用 DBSCAN 聚类算法对说话人嵌入进行聚类
"""
import numpy as np
from typing import List, Tuple, Optional
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score
import logging

logger = logging.getLogger(__name__)

from .models import SpeakerEmbedding, Cluster


class SpeakerClustering:
    """说话人聚类器"""

    def __init__(
        self,
        eps: float = 0.5,
        min_samples: int = 2,
        min_cluster_size: int = 3
    ):
        """
        初始化聚类器

        Args:
            eps: DBSCAN 邻域半径
            min_samples: 最小样本数
            min_cluster_size: 最小聚类大小
        """
        self.eps = eps
        self.min_samples = min_samples
        self.min_cluster_size = min_cluster_size

    def cluster_speakers(
        self,
        embeddings: List[SpeakerEmbedding],
        adjust_parameters: bool = True
    ) -> List[Cluster]:
        """
        对说话人嵌入进行聚类

        Args:
            embeddings: 说话人嵌入列表
            adjust_parameters: 是否自动调整参数

        Returns:
            聚类列表
        """
        if len(embeddings) < 2:
            logger.warning(f"Too few embeddings ({len(embeddings)}), cannot cluster")
            return []

        # 准备数据
        X = np.array([se.embedding for se in embeddings])

        # 初始聚类
        labels = self._dbscan_clustering(X)

        # 调整参数
        if adjust_parameters:
            labels, self.eps, self.min_samples = self._adjust_parameters(X, labels)

        # 合并小聚类
        labels = self._merge_small_clusters(X, labels)

        # 创建聚类对象
        clusters = self._create_clusters(embeddings, labels)

        logger.info(f"Clustering completed: {len(clusters)} clusters from {len(embeddings)} segments")

        return clusters

    def _dbscan_clustering(self, X: np.ndarray) -> np.ndarray:
        """执行 DBSCAN 聚类"""
        dbscan = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            metric="cosine",
            n_jobs=-1
        )
        labels = dbscan.fit_predict(X)

        # 噪声点标记为 -1，转换为正数索引
        if -1 in labels:
            logger.info(f"Found {np.sum(labels == -1)} noise points")

        return labels

    def _adjust_parameters(
        self,
        X: np.ndarray,
        initial_labels: np.ndarray
    ) -> Tuple[np.ndarray, float, int]:
        """
        调整聚类参数

        Args:
            X: 特征矩阵
            initial_labels: 初始标签

        Returns:
            (调整后的标签, eps, min_samples)
        """
        # 计算初始聚类效果
        n_clusters = len(set(initial_labels)) - (1 if -1 in initial_labels else 0)
        n_noise = np.sum(initial_labels == -1)

        logger.info(
            f"Initial clustering: {n_clusters} clusters, {n_noise} noise points"
        )

        # 如果噪声太多，增大 eps
        if n_noise > len(X) * 0.3:
            new_eps = min(self.eps * 1.2, 2.0)
            logger.info(f"Increasing eps: {self.eps} -> {new_eps}")
            self.eps = new_eps

        # 如果聚类太少，减小 min_samples
        if n_clusters < 2:
            new_min_samples = max(self.min_samples - 1, 2)
            logger.info(f"Decreasing min_samples: {self.min_samples} -> {new_min_samples}")
            self.min_samples = new_min_samples

        # 重新聚类
        labels = self._dbscan_clustering(X)

        return labels, self.eps, self.min_samples

    def _merge_small_clusters(
        self,
        X: np.ndarray,
        labels: np.ndarray
    ) -> np.ndarray:
        """
        合并小聚类到最近的聚类

        Args:
            X: 特征矩阵
            labels: 标签

        Returns:
            合并后的标签
        """
        unique_labels = set(labels) - {-1}

        if len(unique_labels) <= 1:
            return labels

        # 计算每个聚类的质心
        centroids = {}
        for label in unique_labels:
            mask = labels == label
            centroids[label] = np.mean(X[mask], axis=0)

        # 合并小聚类
        for label in list(unique_labels):
            cluster_size = np.sum(labels == label)

            if cluster_size < self.min_cluster_size:
                # 找到最近的聚类
                current_centroid = centroids[label]
                nearest_label = self._find_nearest_cluster(
                    current_centroid,
                    centroids,
                    exclude=label
                )

                # 合并
                labels[labels == label] = nearest_label
                logger.info(
                    f"Merged small cluster {label} (size={cluster_size}) "
                    f"into {nearest_label}"
                )

        return labels

    def _find_nearest_cluster(
        self,
        centroid: np.ndarray,
        centroids: dict,
        exclude: int
    ) -> int:
        """找到最近的聚类"""
        min_dist = float("inf")
        nearest_label = -1

        for label, other_centroid in centroids.items():
            if label == exclude:
                continue

            dist = np.linalg.norm(centroid - other_centroid)

            if dist < min_dist:
                min_dist = dist
                nearest_label = label

        return nearest_label

    def _create_clusters(
        self,
        embeddings: List[SpeakerEmbedding],
        labels: np.ndarray
    ) -> List[Cluster]:
        """创建聚类对象"""
        cluster_dict = {}

        for idx, label in enumerate(labels):
            if label == -1:
                continue

            if label not in cluster_dict:
                cluster_dict[label] = []

            cluster_dict[label].append(embeddings[idx])

        clusters = [
            Cluster(
                cluster_id=cluster_id,
                speaker_embeddings=embeddings
            )
            for cluster_id, embeddings in cluster_dict.items()
        ]

        return clusters

    def evaluate_clustering(
        self,
        embeddings: List[SpeakerEmbedding],
        labels: np.ndarray
    ) -> dict:
        """
        评估聚类质量

        Args:
            embeddings: 说话人嵌入列表
            labels: 聚类标签

        Returns:
            评估指标
        """
        X = np.array([se.embedding for se in embeddings])

        # 只评估有标签的数据（排除噪声）
        mask = labels != -1
        X_labeled = X[mask]
        labels_labeled = labels[mask]

        metrics = {}

        # 如果有多个聚类，计算轮廓系数
        if len(set(labels_labeled)) > 1:
            try:
                silhouette = silhouette_score(X_labeled, labels_labeled, metric="cosine")
                metrics["silhouette_score"] = silhouette
            except Exception as e:
                logger.warning(f"Failed to compute silhouette score: {e}")

        # 基础统计
        n_clusters = len(set(labels_labeled))
        n_noise = np.sum(labels == -1)
        cluster_sizes = [np.sum(labels_labeled == l) for l in set(labels_labeled)]

        metrics.update({
            "n_clusters": n_clusters,
            "n_noise": n_noise,
            "avg_cluster_size": np.mean(cluster_sizes) if cluster_sizes else 0,
            "min_cluster_size": np.min(cluster_sizes) if cluster_sizes else 0,
            "max_cluster_size": np.max(cluster_sizes) if cluster_sizes else 0
        })

        logger.info(f"Clustering evaluation: {metrics}")

        return metrics
