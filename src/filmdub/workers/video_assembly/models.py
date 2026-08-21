"""
M11 数据模型
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class AudioSegment:
    """音频片段"""
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
