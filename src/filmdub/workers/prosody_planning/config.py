"""
M08 Prosody Planning 配置
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class M08Config:
    """M08 配置"""

    # 韵律参数范围
    min_speed: float = 0.8
    max_speed: float = 1.3
    min_pitch: float = -12.0
    max_pitch: float = 12.0
    min_pause: float = 0.1
    max_pause: float = 2.0

    # 情绪权重
    emotion_pitch_weight: float = 0.7
    emotion_speed_weight: float = 0.5
    emotion_pause_weight: float = 0.6

    # 性能
    batch_size: int = 32
    max_concurrent_jobs: int = 4
