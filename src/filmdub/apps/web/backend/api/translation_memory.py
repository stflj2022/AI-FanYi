"""翻译记忆 API 路由"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.core.orchestrator_db import get_db
from filmdub.apps.web.backend.api.schemas.translation_schemas import (
    TranslationMemoryEntryCreate,
    TranslationMemoryEntryUpdate,
    TranslationMemoryEntryResponse,
    TranslationMemoryListResponse,
    GlossaryTermCreate,
    GlossaryTermUpdate,
    GlossaryTermResponse,
    GlossaryTermListResponse,
    TranslationStatisticsResponse,
)
from filmdub.apps.web.backend.services.translation_memory_service import TranslationMemoryService

router = APIRouter()


# ==================== 翻译记忆条目 ====================

@router.get("/entries", response_model=TranslationMemoryListResponse)
async def get_translation_entries(
    project_id: Optional[UUID] = Query(None, description="项目 ID"),
    source_lang: Optional[str] = Query(None, description="源语言"),
    target_lang: Optional[str] = Query(None, description="目标语言"),
    character_name: Optional[str] = Query(None, description="人物名称"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取翻译记忆条目列表"""
    skip = (page - 1) * page_size

    entries, total = await TranslationMemoryService.get_translation_entries(
        db=db,
        project_id=project_id,
        source_lang=source_lang,
        target_lang=target_lang,
        character_name=character_name,
        search=search,
        skip=skip,
        limit=page_size,
    )

    return TranslationMemoryListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=entries,
    )


@router.get("/entries/{entry_id}", response_model=TranslationMemoryEntryResponse)
async def get_translation_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取翻译记忆条目详情"""
    entry = await TranslationMemoryService.get_translation_entry_by_id(db, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Translation memory entry {entry_id} not found",
        )
    return entry


@router.post("/entries", response_model=TranslationMemoryEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_translation_entry(
    entry: TranslationMemoryEntryCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建翻译记忆条目"""
    new_entry = await TranslationMemoryService.create_translation_entry(
        db=db,
        project_id=entry.project_id,
        source_text=entry.source_text,
        translated_text=entry.translated_text,
        source_lang=entry.source_lang,
        target_lang=entry.target_lang,
        context=entry.context,
        character_name=entry.character_name,
        scene_description=entry.scene_description,
        similarity_score=entry.similarity_score,
    )

    return new_entry


@router.put("/entries/{entry_id}", response_model=TranslationMemoryEntryResponse)
async def update_translation_entry(
    entry_id: UUID,
    entry: TranslationMemoryEntryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新翻译记忆条目"""
    updated_entry = await TranslationMemoryService.update_translation_entry(
        db=db,
        entry_id=entry_id,
        source_text=entry.source_text,
        translated_text=entry.translated_text,
        source_lang=entry.source_lang,
        target_lang=entry.target_lang,
        context=entry.context,
        character_name=entry.character_name,
        scene_description=entry.scene_description,
        similarity_score=entry.similarity_score,
    )

    if not updated_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Translation memory entry {entry_id} not found",
        )

    return updated_entry


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_translation_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除翻译记忆条目"""
    success = await TranslationMemoryService.delete_translation_entry(db, entry_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Translation memory entry {entry_id} not found",
        )


@router.post("/entries/{entry_id}/use", response_model=TranslationMemoryEntryResponse)
async def use_translation_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """标记翻译记忆条目为已使用（增加使用计数）"""
    entry = await TranslationMemoryService.increment_usage_count(db, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Translation memory entry {entry_id} not found",
        )
    return entry


# ==================== 术语库 ====================

@router.get("/glossary", response_model=GlossaryTermListResponse)
async def get_glossary_terms(
    project_id: Optional[UUID] = Query(None, description="项目 ID"),
    category: Optional[str] = Query(None, description="分类"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取术语列表"""
    skip = (page - 1) * page_size

    terms, total = await TranslationMemoryService.get_glossary_terms(
        db=db,
        project_id=project_id,
        category=category,
        search=search,
        skip=skip,
        limit=page_size,
    )

    return GlossaryTermListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=terms,
    )


@router.get("/glossary/{term_id}", response_model=GlossaryTermResponse)
async def get_glossary_term(
    term_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取术语详情"""
    term = await TranslationMemoryService.get_glossary_term_by_id(db, term_id)
    if not term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Glossary term {term_id} not found",
        )
    return term


@router.post("/glossary", response_model=GlossaryTermResponse, status_code=status.HTTP_201_CREATED)
async def create_glossary_term(
    term: GlossaryTermCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建术语"""
    new_term = await TranslationMemoryService.create_glossary_term(
        db=db,
        project_id=term.project_id,
        source_term=term.source_term,
        target_term=term.target_term,
        category=term.category,
        notes=term.notes,
        examples=term.examples,
    )

    return new_term


@router.put("/glossary/{term_id}", response_model=GlossaryTermResponse)
async def update_glossary_term(
    term_id: UUID,
    term: GlossaryTermUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新术语"""
    updated_term = await TranslationMemoryService.update_glossary_term(
        db=db,
        term_id=term_id,
        source_term=term.source_term,
        target_term=term.target_term,
        category=term.category,
        notes=term.notes,
        examples=term.examples,
    )

    if not updated_term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Glossary term {term_id} not found",
        )

    return updated_term


@router.delete("/glossary/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_glossary_term(
    term_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除术语"""
    success = await TranslationMemoryService.delete_glossary_term(db, term_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Glossary term {term_id} not found",
        )


@router.post("/glossary/{term_id}/use", response_model=GlossaryTermResponse)
async def use_glossary_term(
    term_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """标记术语为已使用（增加使用计数）"""
    term = await TranslationMemoryService.increment_term_usage_count(db, term_id)
    if not term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Glossary term {term_id} not found",
        )
    return term


# ==================== 统计 ====================

@router.get("/statistics", response_model=TranslationStatisticsResponse)
async def get_translation_statistics(
    project_id: Optional[UUID] = Query(None, description="项目 ID，不指定则返回全局统计"),
    db: AsyncSession = Depends(get_db),
):
    """获取翻译统计"""
    stats = await TranslationMemoryService.get_statistics(db, project_id)
    return TranslationStatisticsResponse(**stats)
