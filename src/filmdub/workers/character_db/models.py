"""
M04 数据模型
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class Gender(Enum):
    """性别"""
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"
    OTHER = "other"


class RoleType(Enum):
    """角色类型"""
    PROTAGONIST = "protagonist"      # 主角
    ANTAGONIST = "antagonist"        # 反派
    SUPPORTING = "supporting"        # 配角
    MINOR = "minor"                  # 次要角色
    NARRATOR = "narrator"            # 旁白
    CROWD = "crowd"                  # 群众
    UNKNOWN = "unknown"              # 未知


@dataclass
class SpeakerEmbedding:
    """说话人嵌入"""
    segment_id: str
    start_time: float
    end_time: float
    embedding: List[float]
    confidence: float
    text: str


@dataclass
class Cluster:
    """聚类"""
    cluster_id: int
    speaker_embeddings: List[SpeakerEmbedding]
    centroid: Optional[List[float]] = None
    size: int = 0

    def __post_init__(self):
        """初始化后处理"""
        self.size = len(self.speaker_embeddings)
        if self.speaker_embeddings and self.centroid is None:
            self._compute_centroid()

    def _compute_centroid(self):
        """计算质心"""
        import numpy as np

        embeddings = np.array([se.embedding for se in self.speaker_embeddings])
        self.centroid = np.mean(embeddings, axis=0).tolist()


@dataclass
class Character:
    """人物"""
    character_id: str
    name: str
    gender: Gender = Gender.UNKNOWN
    age_range: Optional[str] = None
    role_type: RoleType = RoleType.UNKNOWN
    description: Optional[str] = None
    tmdb_id: Optional[int] = None
    tmdb_name: Optional[str] = None
    tmdb_image: Optional[str] = None
    total_segments: int = 0
    total_duration: float = 0.0
    confidence: float = 0.0
    reference_embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "character_id": self.character_id,
            "name": self.name,
            "gender": self.gender.value,
            "age_range": self.age_range,
            "role_type": self.role_type.value,
            "description": self.description,
            "tmdb_id": self.tmdb_id,
            "tmdb_name": self.tmdb_name,
            "tmdb_image": self.tmdb_image,
            "total_segments": self.total_segments,
            "total_duration": self.total_duration,
            "confidence": self.confidence
        }


@dataclass
class CharacterRelationship:
    """人物关系"""
    from_character_id: str
    to_character_id: str
    relationship_type: str  # "family", "friend", "enemy", "colleague", "other"
    confidence: float
    description: Optional[str] = None
