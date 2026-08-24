"""翻译记忆相关的 Pydantic schemas"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TranslationMemoryEntryCreate(BaseModel):
    """创建翻译记忆条目请求"""
    project_id: Optional[UUID] = Field(None, description="项目 ID（可选，全局条目可为空）")
    source_text: str = Field(..., min_length=1, description="原文")
    translated_text: str = Field(..., min_length=1, description="译文")
    source_lang: str = Field(..., min_length=2, max_length=10, description="源语言代码")
    target_lang: str = Field(..., min_length=2, max_length=10, description="目标语言代码")
    context: Optional[str] = Field(None, description="上下文")
    character_name: Optional[str] = Field(None, description="人物名称")
    scene_description: Optional[str] = Field(None, description="场景描述")
    similarity_score: Optional[float] = Field(None, ge=0, le=1, description="相似度分数")


class TranslationMemoryEntryUpdate(BaseModel):
    """更新翻译记忆条目请求"""
    source_text: Optional[str] = Field(None, min_length=1)
    translated_text: Optional[str] = Field(None, min_length=1)
    source_lang: Optional[str] = Field(None, min_length=2, max_length=10)
    target_lang: Optional[str] = Field(None, min_length=2, max_length=10)
    context: Optional[str] = None
    character_name: Optional[str] = None
    scene_description: Optional[str] = None
    similarity_score: Optional[float] = Field(None, ge=0, le=1)


class TranslationMemoryEntryResponse(BaseModel):
    """翻译记忆条目响应"""
    id: UUID
    project_id: Optional[UUID] = None
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    context: Optional[str] = None
    character_name: Optional[str] = None
    scene_description: Optional[str] = None
    usage_count: int
    last_used: Optional[datetime] = None
    similarity_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TranslationMemoryListResponse(BaseModel):
    """翻译记忆列表响应"""
    total: int
    page: int
    page_size: int
    items: List[TranslationMemoryEntryResponse]


class GlossaryTermCreate(BaseModel):
    """创建术语条目请求"""
    project_id: Optional[UUID] = Field(None, description="项目 ID（可选，全局术语可为空）")
    source_term: str = Field(..., min_length=1, max_length=500, description="源术语")
    target_term: str = Field(..., min_length=1, max_length=500, description="目标术语")
    category: Optional[str] = Field(None, max_length=100, description="分类（人物/地名/组织等）")
    notes: Optional[str] = Field(None, description="备注")
    examples: Optional[List[str]] = Field(None, description="例句")


class GlossaryTermUpdate(BaseModel):
    """更新术语条目请求"""
    source_term: Optional[str] = Field(None, min_length=1, max_length=500)
    target_term: Optional[str] = Field(None, min_length=1, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    examples: Optional[List[str]] = None


class GlossaryTermResponse(BaseModel):
    """术语条目响应"""
    id: UUID
    project_id: Optional[UUID] = None
    source_term: str
    target_term: str
    category: Optional[str] = None
    notes: Optional[str] = None
    examples: Optional[List[str]] = None
    usage_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GlossaryTermListResponse(BaseModel):
    """术语列表响应"""
    total: int
    page: int
    page_size: int
    items: List[GlossaryTermResponse]


class TranslationMemoryQueryParams(BaseModel):
    """翻译记忆查询参数"""
    project_id: Optional[UUID] = None
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    character_name: Optional[str] = None
    search: Optional[str] = None  # 搜索原文或译文
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class GlossaryQueryParams(BaseModel):
    """术语查询参数"""
    project_id: Optional[UUID] = None
    category: Optional[str] = None
    search: Optional[str] = None  # 搜索源术语或目标术语
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TranslationStatisticsResponse(BaseModel):
    """翻译统计响应"""
    total_entries: int
    total_glossary_terms: int
    language_pairs: List[Dict[str, Any]]
    most_used_translations: List[Dict[str, Any]]
    most_used_terms: List[Dict[str, Any]]
