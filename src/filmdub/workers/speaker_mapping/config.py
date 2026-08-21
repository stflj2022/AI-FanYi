"""
M06 Speaker Mapping 配置
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class M06Config:
    """M06 配置"""

    # 相似度阈值
    similarity_threshold: float = 0.7
    voice_similarity_threshold: float = 0.8

    # 跨集一致性
    enable_cross_episode_consistency: bool = True
    cross_episode_similarity_threshold: float = 0.85

    # 音色分配
    reuse_voice_profiles: bool = True
    max_voice_profiles_per_character: int = 3

    # 性能
    max_concurrent_jobs: int = 4
