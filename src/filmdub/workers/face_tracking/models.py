"""Face tracking module models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import numpy as np


@dataclass
class FaceDetection:
    """Face detection result."""

    face_id: str
    bbox: List[int]  # [x, y, width, height]
    confidence: float
    landmarks: Optional[List[List[float]]] = None  # Facial landmarks
    embedding: Optional[np.ndarray] = None
    frame_number: int = 0
    timestamp: float = 0.0


@dataclass
class FaceTrack:
    """Face track across multiple frames."""

    track_id: str
    face_id: Optional[UUID] = None  # Mapped to character
    detections: List[FaceDetection] = field(default_factory=list)
    first_frame: int = 0
    last_frame: int = 0
    total_frames: int = 0
    average_confidence: float = 0.0
    representative_embedding: Optional[np.ndarray] = None


@dataclass
class CharacterAppearance:
    """Character appearance in video."""

    character_id: Optional[UUID]
    character_name: str = ""
    track_ids: List[str] = field(default_factory=list)
    appearances: List[Dict] = field(default_factory=list)
    total_screen_time: float = 0.0
    first_appearance: float = 0.0
    last_appearance: float = 0.0


@dataclass
class M03Input:
    """M03 Worker input."""

    project_id: UUID
    job_id: UUID
    video_path: str
    character_database: Optional[Dict] = None
    sampling_rate: int = 5


@dataclass
class M03Output:
    """M03 Worker output."""

    project_id: UUID
    job_id: UUID
    video_path: str
    total_frames: int
    fps: float
    duration: float
    faces_detected: int
    tracks_created: int
    characters_found: int
    face_tracks: List[FaceTrack]
    character_appearances: List[CharacterAppearance]
    embeddings_file: Optional[str] = None
    crops_dir: Optional[str] = None
