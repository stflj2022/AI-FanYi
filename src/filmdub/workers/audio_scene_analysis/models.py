"""
M05 数据模型
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class SpeakerSegment:
    """说话人片段"""
    speaker_id: str
    start_time: float
    end_time: float
    confidence: float
    text: Optional[str] = None


@dataclass
class SpeakerEmbedding:
    """说话人嵌入"""
    speaker_id: str
    start_time: float
    end_time: float
    embedding: List[float]
    confidence: float
    segment_count: int


@dataclass
class AudioFeatures:
    """音频特征"""
    speaker_id: str
    start_time: float
    end_time: float

    # 音高特征
    pitch_mean: float
    pitch_std: float
    pitch_min: float
    pitch_max: float

    # 能量特征
    energy_mean: float
    energy_std: float

    # 频谱特征
    spectral_centroid_mean: float
    spectral_centroid_std: float
    spectral_rolloff_mean: float
    spectral_rolloff_std: float

    # MFCC 特征
    mfcc_mean: List[float]
    mfcc_std: List[float]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "speaker_id": self.speaker_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "pitch_mean": self.pitch_mean,
            "pitch_std": self.pitch_std,
            "pitch_min": self.pitch_min,
            "pitch_max": self.pitch_max,
            "energy_mean": self.energy_mean,
            "energy_std": self.energy_std,
            "spectral_centroid_mean": self.spectral_centroid_mean,
            "spectral_centroid_std": self.spectral_centroid_std,
            "spectral_rolloff_mean": self.spectral_rolloff_mean,
            "spectral_rolloff_std": self.spectral_rolloff_std,
            "mfcc_mean": self.mfcc_mean,
            "mfcc_std": self.mfcc_std
        }


@dataclass
class DiarizationResult:
    """说话人分离结果"""
    segments: List[SpeakerSegment]
    num_speakers: int
    total_duration: float

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "segments": [
                {
                    "speaker_id": s.speaker_id,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "confidence": s.confidence,
                    "text": s.text
                }
                for s in self.segments
            ],
            "num_speakers": self.num_speakers,
            "total_duration": self.total_duration
        }
