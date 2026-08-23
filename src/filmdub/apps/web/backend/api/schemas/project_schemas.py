"""项目相关的 Pydantic schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum
import uuid

from filmdub.core.models import WebProject, ProjectStatus


class ProjectStatusEnum(str, Enum):
    """项目状态枚举"""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class ProjectCreate(BaseModel):
    """创建项目请求"""
    name: str = Field(..., min_length=1, max_length=255, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    title: Optional[str] = Field(None, max_length=255, description="影视标题")
    title_en: Optional[str] = Field(None, max_length=255, description="英文标题")
    season: Optional[int] = Field(None, ge=1, description="季数")
    episode: Optional[int] = Field(None, ge=1, description="集数")
    year: Optional[int] = Field(None, ge=1900, le=2100, description="年份")
    original_language: Optional[str] = Field(None, max_length=10, description="原始语言")
    target_language: str = Field("zh", max_length=10, description="目标语言")
    media_type: Optional[str] = Field(None, max_length=50, description="媒体类型")
    tmdb_id: Optional[int] = Field(None, description="TMDB ID")
    imdb_id: Optional[str] = Field(None, max_length=20, description="IMDB ID")
    config: Optional[dict] = Field(None, description="项目配置")


class ProjectUpdate(BaseModel):
    """更新项目请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    title: Optional[str] = Field(None, max_length=255, description="影视标题")
    title_en: Optional[str] = Field(None, max_length=255, description="英文标题")
    season: Optional[int] = Field(None, ge=1, description="季数")
    episode: Optional[int] = Field(None, ge=1, description="集数")
    year: Optional[int] = Field(None, ge=1900, le=2100, description="年份")
    original_language: Optional[str] = Field(None, max_length=10, description="原始语言")
    target_language: Optional[str] = Field(None, max_length=10, description="目标语言")
    media_type: Optional[str] = Field(None, max_length=50, description="媒体类型")
    tmdb_id: Optional[int] = Field(None, description="TMDB ID")
    imdb_id: Optional[str] = Field(None, max_length=20, description="IMDB ID")
    config: Optional[dict] = Field(None, description="项目配置")
    status: Optional[ProjectStatusEnum] = Field(None, description="项目状态")


class ProjectResponse(BaseModel):
    """项目响应"""
    id: str
    name: str
    description: Optional[str]
    title: Optional[str]
    title_en: Optional[str]
    season: Optional[int]
    episode: Optional[int]
    year: Optional[int]
    original_language: Optional[str]
    target_language: str
    status: str
    owner_id: str  # 映射到 created_by
    media_type: Optional[str]
    tmdb_id: Optional[int]
    imdb_id: Optional[str]
    config: Optional[dict]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def model_validate(cls, obj):
        """从数据库模型验证，自动转换 UUID"""
        if hasattr(obj, 'id') and isinstance(obj.id, uuid.UUID):
            obj_dict = {
                'id': str(obj.id),
                'name': obj.name,
                'description': obj.description,
                'title': obj.title,
                'title_en': obj.title_en,
                'season': obj.season,
                'episode': obj.episode,
                'year': obj.year,
                'original_language': obj.original_language,
                'target_language': obj.target_language,
                'status': obj.status.value if isinstance(obj.status, ProjectStatus) else obj.status,
                'owner_id': str(obj.created_by) if obj.created_by else '',
                'media_type': obj.media_type,
                'tmdb_id': obj.tmdb_id,
                'imdb_id': obj.imdb_id,
                'config': obj.config,
                'created_at': obj.created_at,
                'updated_at': obj.updated_at,
                'started_at': obj.started_at,
                'completed_at': obj.completed_at,
            }
            return cls(**obj_dict)
        return super().model_validate(obj)


class ProjectListResponse(BaseModel):
    """项目列表响应"""
    total: int
    page: int
    page_size: int
    items: list[ProjectResponse]
