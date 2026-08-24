"""
M11 数据模型
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from pathlib import Path


class AudioTrackType(str, Enum):
    """音频轨道类型"""
    DIALOGUE = "dialogue"  # AI 对白
    BACKGROUND = "background"  # 背景音乐
    AMBIENT = "ambient"  # 环境音
    EFFECTS = "effects"  # 音效
    ORIGINAL = "original"  # 原声（需要去除）


@dataclass
class AudioSegment:
    """音频片段（用于 AI 对白）"""
    dialogue_id: str
    audio_path: str
    start_time: float
    end_time: float
    target_start_time: float
    target_end_time: float

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "dialogue_id": self.dialogue_id,
            "audio_path": self.audio_path,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "target_start_time": self.target_start_time,
            "target_end_time": self.target_end_time
        }


@dataclass
class AudioTrack:
    """音频轨道（背景音乐/环境音/音效）"""
    track_type: AudioTrackType
    audio_path: str
    start_time: float = 0.0  # 轨道开始时间
    end_time: Optional[float] = None  # 轨道结束时间（None 表示到结束）
    volume: float = 1.0  # 音量因子
    fade_in: float = 0.0  # 淡入时长（秒）
    fade_out: float = 0.0  # 淡出时长（秒）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "track_type": self.track_type.value,
            "audio_path": self.audio_path,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "volume": self.volume,
            "fade_in": self.fade_in,
            "fade_out": self.fade_out,
        }


@dataclass
class SubtitleEntry:
    """字幕条目"""
    index: int
    start_time: float
    end_time: float
    text: str
    speaker_id: Optional[str] = None

    def to_srt(self) -> str:
        """转换为 SRT 格式"""
        start = self._seconds_to_srt_time(self.start_time)
        end = self._seconds_to_srt_time(self.end_time)

        return f"{self.index}\n{start} --> {end}\n{self.text}\n"

    def to_ass(self) -> str:
        """转换为 ASS 格式"""
        start = self._seconds_to_ass_time(self.start_time)
        end = self._seconds_to_ass_time(self.end_time)

        return f"Dialogue: 0,{start},{end},Default,,0,0,0,,{self.text}"

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """将秒数转换为 SRT 时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _seconds_to_ass_time(seconds: float) -> str:
        """将秒数转换为 ASS 时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int((seconds % 1) * 100)

        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


@dataclass
class AssemblyResult:
    """组装结果"""
    project_id: str
    video_path: str
    duration: float
    resolution: str
    file_size: int
    audio_codec: str
    video_codec: str
    subtitle_path: Optional[str] = None
    lufs_level: Optional[float] = None  # LUFS 响度
    
    # 分离的音轨路径
    separated_tracks: Dict[str, Path] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "project_id": self.project_id,
            "video_path": self.video_path,
            "duration": self.duration,
            "resolution": self.resolution,
            "file_size": self.file_size,
            "audio_codec": self.audio_codec,
            "video_codec": self.video_codec,
            "subtitle_path": self.subtitle_path
        }
