"""
M05 Audio & Scene Analysis 配置
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class M05Config:
    """M05 配置"""

    # 模型路径
    diarization_model: str = "pyannote/speaker-diarization-3.1"
    embedding_model: str = "speechbrain/spkrec-ecapa-voxceleb"
    # HuggingFace token（访问 gated 模型时需要，如 pyannote 系列）
    hf_token: Optional[str] = None

    # 音频参数
    sample_rate: int = 16000
    chunk_length_seconds: int = 30

    # 说话人分离参数
    min_speaker_duration: float = 1.0
    max_speaker_duration: float = 60.0

    # 嵌入参数
    embedding_dim: int = 192
    embedding_batch_size: int = 16

    # 特征提取参数
    n_mfcc: int = 13
    n_fft: int = 2048
    hop_length: int = 512

    # 性能
    device: str = "cpu"
    max_concurrent_jobs: int = 2
