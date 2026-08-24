"""
M09 Voice Synthesis 配置
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class M09Config:
    """M09 配置"""

    # TTS 模型
    default_model: str = "cosyvoice"
    model_path: Optional[str] = None

    # CosyVoice 配置
    cosyvoice_model_name: str = "CosyVoice-300M"
    cosyvoice_device: str = "cuda"

    # F5-TTS 配置（可选）
    enable_f5_tts: bool = False
    f5_tts_model_path: Optional[str] = None

    # 音频参数
    sample_rate: int = 24000
    audio_format: str = "wav"

    # 音频处理
    enable_pitch_shift: bool = True
    enable_time_stretch: bool = True
    pitch_shift_lib: str = "pyrubberband"  # or "librosa"

    # 批量合成
    batch_size: int = 8
    max_concurrent_jobs: int = 4
    synthesis_timeout: int = 60

    # 统一走 Adapter（ticket-035）：True 时经 model_manager 的 Adapter 接口合成，后端可配置切换
    use_adapter: bool = True

    # 缓存
    enable_cache: bool = True
    cache_dir: str = "./cache/m09"
