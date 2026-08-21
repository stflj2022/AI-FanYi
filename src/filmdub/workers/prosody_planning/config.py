"""
M08 Prosody Planning 配置
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class M08Config:
    """M08 配置"""

    # 韵律参数范围
    speed_min: float = 0.5
    speed_max: float = 2.0
    pitch_min: float = 0.5
    pitch_max: float = 2.0
    volume_min: float = 0.5
    volume_max: float = 1.5

    # 停顿参数
    sentence_pause: float = 0.5  # 句末停顿（秒）
    clause_pause: float = 0.25   # 分句停顿（秒）
    word_pause: float = 0.1      # 词间停顿（秒）

    # 性能
    max_concurrent_jobs: int = 4
