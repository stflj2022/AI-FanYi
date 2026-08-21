"""
M06 Speaker Mapping 配置
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class M06Config:
    """M06 配置"""

    # 相似度阈值
    voice_similarity_threshold: float = 0.75

    # 跨集一致性
    enable_cross_episode_consistency: bool = True
    consistency_threshold: float = 0.85

    # 音色分配
    auto_create_profiles: bool = True
    reuse_profiles: bool = True

    # 性能
    batch_size: int = 32
    max_concurrent_jobs: int = 4
