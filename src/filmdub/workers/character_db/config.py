"""
M04 Character Database 配置
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class M04Config:
    """M04 配置"""

    # 聚类参数
    clustering_eps: float = 0.5
    clustering_min_samples: int = 2

    # 相似度阈值
    similarity_threshold: float = 0.7

    # TMDB API
    tmdb_api_key: Optional[str] = None

    # LLM 配置
    llm_endpoint: str = "http://localhost:8000"
    llm_model: str = "qwen"

    # 置信度阈值
    auto_confirm_threshold: float = 0.9
    manual_review_threshold: float = 0.7

    # 性能
    batch_size: int = 32
    max_concurrent_jobs: int = 4
