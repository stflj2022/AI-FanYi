"""
M11 数据模型
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class VideoArtifact:
    """视频 Artifact"""
    artifact_id: str
    project_id: str
    file_path: str
    duration: float
    width: int
    height: int
    fps: float
    file_size: int

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "artifact_id": self.artifact_id,
            "project_id": self.project_id,
            "file_path": self.file_path,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "file_size": self.file_size
        }


@dataclass
class AudioSyncPoint:
    """音视频同步点"""
    time: float
    offset: float
    confidence: float


@dataclass
class AssemblyResult:
    """组装结果"""
    status: str
    video_artifact: Optional[VideoArtifact] = None
    error: Optional[str] = None
    progress: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status,
            "video_artifact": self.video_artifact.to_dict() if self.video_artifact else None,
            "error": self.error,
            "progress": self.progress,
            "metadata": self.metadata
        }
