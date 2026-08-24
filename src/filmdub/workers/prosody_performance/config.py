"""
M10 Prosody & Performance 配置
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class M10Config:
    """M10 模块配置"""

    # 音频处理参数
    sample_rate: int = 22050

    # 音高变换范围
    pitch_min: float = 0.5  # 降低一个八度
    pitch_max: float = 2.0  # 提高一个八度

    # 语速变换范围
    speed_min: float = 0.5  # 0.5x 语速
    speed_max: float = 2.0  # 2x 语速

    # 音量变换范围
    volume_min: float = 0.3  # -10dB
    volume_max: float = 2.0  # +6dB

    # 停顿参数（秒）
    pause_min: float = 0.1
    pause_max: float = 1.0
    default_pause: float = 0.3

    # 呼吸声参数
    breath_probability: float = 0.15  # 15% 概率添加呼吸声
    breath_volume: float = 0.2  # 呼吸声音量

    # 韵律处理
    enable_prosody_enhancement: bool = True
    prosody_strength: float = 0.7  # 韵律增强强度

    # 情绪映射
    emotion_params: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "neutral": {"pitch": 1.0, "speed": 1.0, "volume": 1.0},
        "happy": {"pitch": 1.15, "speed": 1.1, "volume": 1.1},
        "sad": {"pitch": 0.85, "speed": 0.9, "volume": 0.85},
        "angry": {"pitch": 1.1, "speed": 1.2, "volume": 1.3},
        "fear": {"pitch": 1.2, "speed": 1.3, "volume": 0.9},
        "surprised": {"pitch": 1.2, "speed": 1.15, "volume": 1.1},
        "calm": {"pitch": 0.95, "speed": 0.95, "volume": 0.95},
    })

    # 输出质量
    output_format: str = "wav"
    output_bitrate: str = "192k"

    # 缓存
    enable_cache: bool = True
    cache_dir: Optional[str] = None

    def get_emotion_params(self, emotion: str) -> Dict[str, float]:
        """
        获取情绪对应的韵律参数

        Args:
            emotion: 情绪类型

        Returns:
            韵律参数字典
        """
        return self.emotion_params.get(emotion.lower(), self.emotion_params["neutral"])

    def clamp_pitch(self, pitch: float) -> float:
        """限制音高在有效范围内"""
        return max(self.pitch_min, min(self.pitch_max, pitch))

    def clamp_speed(self, speed: float) -> float:
        """限制语速在有效范围内"""
        return max(self.speed_min, min(self.speed_max, speed))

    def clamp_volume(self, volume: float) -> float:
        """限制音量在有效范围内"""
        return max(self.volume_min, min(self.volume_max, volume))
