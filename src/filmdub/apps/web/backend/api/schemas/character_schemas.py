"""人物相关的 Pydantic schemas"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Gender(str, Enum):
    """性别"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class AgeRange(str, Enum):
    """年龄段"""
    CHILD = "child"  # 0-12
    TEEN = "teen"  # 13-19
    YOUNG_ADULT = "young_adult"  # 20-35
    MIDDLE_AGED = "middle_aged"  # 36-55
    SENIOR = "senior"  # 56+


class RoleType(str, Enum):
    """角色类型"""
    PROTAGONIST = "protagonist"  # 主角
    ANTAGONIST = "antagonist"  # 反派
    SUPPORTING = "supporting"  # 配角
    EXTRAS = "extras"  # 群演
    NARRATOR = "narrator"  # 旁白
    OTHER = "other"  # 其他


class CharacterCreate(BaseModel):
    """创建人物请求"""
    project_id: UUID = Field(..., description="项目 ID")
    name: str = Field(..., min_length=1, max_length=255, description="人物名称")
    gender: Optional[Gender] = Field(None, description="性别")
    age_range: Optional[AgeRange] = Field(None, description="年龄段")
    role_type: Optional[RoleType] = Field(None, description="角色类型")
    description: Optional[str] = Field(None, description="人物描述")
    original_actor: Optional[str] = Field(None, description="原声演员")
    avatar_url: Optional[str] = Field(None, description="头像 URL")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class CharacterUpdate(BaseModel):
    """更新人物请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    gender: Optional[Gender] = None
    age_range: Optional[AgeRange] = None
    role_type: Optional[RoleType] = None
    description: Optional[str] = None
    original_actor: Optional[str] = None
    avatar_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VoiceProfileResponse(BaseModel):
    """音色档案响应"""
    id: UUID
    character_id: UUID
    voice_id: str
    provider: str
    model: Optional[str] = None
    style: Optional[str] = None
    similarity_score: Optional[float] = None
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CharacterResponse(BaseModel):
    """人物响应"""
    id: UUID
    project_id: UUID
    name: str
    gender: Optional[str] = None
    age_range: Optional[str] = None
    role_type: Optional[str] = None
    description: Optional[str] = None
    original_actor: Optional[str] = None
    avatar_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    voice_profiles: Optional[List[VoiceProfileResponse]] = None

    # 时间
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CharacterListResponse(BaseModel):
    """人物列表响应"""
    total: int
    page: int
    page_size: int
    items: List[CharacterResponse]


class VoiceProfileCreate(BaseModel):
    """创建音色档案请求"""
    voice_id: str = Field(..., description="音色 ID")
    provider: str = Field(..., description="提供商")
    model: Optional[str] = Field(None, description="模型")
    style: Optional[str] = Field(None, description="风格")
    similarity_score: Optional[float] = Field(None, ge=0, le=1, description="相似度分数")
    is_active: bool = Field(True, description="是否激活")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class VoiceProfileUpdate(BaseModel):
    """更新音色档案请求"""
    voice_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    style: Optional[str] = None
    similarity_score: Optional[float] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class CharacterQueryParams(BaseModel):
    """人物查询参数"""
    project_id: Optional[UUID] = None
    gender: Optional[Gender] = None
    age_range: Optional[AgeRange] = None
    role_type: Optional[RoleType] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
