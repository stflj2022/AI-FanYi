"""人物数据库 API 路由"""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.core.orchestrator_db import get_db
from filmdub.apps.web.backend.api.schemas.character_schemas import (
    CharacterCreate,
    CharacterUpdate,
    CharacterResponse,
    CharacterListResponse,
    VoiceProfileCreate,
    VoiceProfileUpdate,
    VoiceProfileResponse,
)
from filmdub.apps.web.backend.services.character_service import CharacterService

router = APIRouter()


@router.get("", response_model=CharacterListResponse)
async def get_characters(
    project_id: Optional[UUID] = Query(None, description="项目 ID"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    gender: Optional[str] = Query(None, description="性别筛选"),
    age_range: Optional[str] = Query(None, description="年龄段筛选"),
    role_type: Optional[str] = Query(None, description="角色类型筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取人物列表"""
    skip = (page - 1) * page_size

    characters, total = await CharacterService.get_characters(
        db=db,
        project_id=project_id,
        search=search,
        gender=gender,
        age_range=age_range,
        role_type=role_type,
        skip=skip,
        limit=page_size,
    )

    return CharacterListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=characters,
    )


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取人物详情"""
    character = await CharacterService.get_character_by_id(db, character_id)
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )
    return character


@router.post("", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def create_character(
    character: CharacterCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建人物"""
    # 检查是否已存在同名人物
    existing = await CharacterService.get_character_by_name(
        db, character.project_id, character.name
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Character with name '{character.name}' already exists in this project",
        )

    new_character = await CharacterService.create_character(
        db=db,
        project_id=character.project_id,
        name=character.name,
        gender=character.gender,
        age_range=character.age_range,
        role_type=character.role_type,
        description=character.description,
        original_actor=character.original_actor,
        avatar_url=character.avatar_url,
        metadata=character.metadata,
    )

    return new_character


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: UUID,
    character: CharacterUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新人物"""
    updated_character = await CharacterService.update_character(
        db=db,
        character_id=character_id,
        name=character.name,
        gender=character.gender,
        age_range=character.age_range,
        role_type=character.role_type,
        description=character.description,
        original_actor=character.original_actor,
        avatar_url=character.avatar_url,
        metadata=character.metadata,
    )

    if not updated_character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )

    return updated_character


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
    character_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除人物"""
    success = await CharacterService.delete_character(db, character_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )


@router.post("/{character_id}/avatar", response_model=CharacterResponse)
async def upload_character_avatar(
    character_id: UUID,
    file: UploadFile = File(..., description="头像文件"),
    db: AsyncSession = Depends(get_db),
):
    """上传人物头像"""
    character = await CharacterService.get_character_by_id(db, character_id)
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )

    # 验证文件类型
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}",
        )

    # TODO: 实际上传到存储服务（MinIO/S3）
    # 这里暂时返回模拟 URL
    avatar_url = f"/api/v1/characters/{character_id}/avatar/{file.filename}"

    updated_character = await CharacterService.update_character(
        db=db,
        character_id=character_id,
        avatar_url=avatar_url,
    )

    return updated_character


@router.get("/{character_id}/voice-profiles", response_model=List[VoiceProfileResponse])
async def get_voice_profiles(
    character_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取人物的音色档案"""
    # 先验证人物存在
    character = await CharacterService.get_character_by_id(db, character_id)
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )

    voice_profiles = await CharacterService.get_voice_profiles(db, character_id)
    return voice_profiles


@router.post("/{character_id}/voice-profiles", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_voice_profile(
    character_id: UUID,
    voice_profile: VoiceProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建音色档案"""
    # 先验证人物存在
    character = await CharacterService.get_character_by_id(db, character_id)
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )

    new_voice_profile = await CharacterService.create_voice_profile(
        db=db,
        character_id=character_id,
        voice_id=voice_profile.voice_id,
        provider=voice_profile.provider,
        model=voice_profile.model,
        style=voice_profile.style,
        similarity_score=voice_profile.similarity_score,
        is_active=voice_profile.is_active,
        metadata=voice_profile.metadata,
    )

    return new_voice_profile


@router.put("/voice-profiles/{voice_profile_id}", response_model=VoiceProfileResponse)
async def update_voice_profile(
    voice_profile_id: UUID,
    voice_profile: VoiceProfileUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新音色档案"""
    updated_profile = await CharacterService.update_voice_profile(
        db=db,
        voice_profile_id=voice_profile_id,
        voice_id=voice_profile.voice_id,
        provider=voice_profile.provider,
        model=voice_profile.model,
        style=voice_profile.style,
        similarity_score=voice_profile.similarity_score,
        is_active=voice_profile.is_active,
        metadata=voice_profile.metadata,
    )

    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voice profile {voice_profile_id} not found",
        )

    return updated_profile


@router.delete("/voice-profiles/{voice_profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice_profile(
    voice_profile_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除音色档案"""
    success = await CharacterService.delete_voice_profile(db, voice_profile_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voice profile {voice_profile_id} not found",
        )


# ==================== 跨集复用 ====================

@router.get("/available/{project_id}", response_model=List[dict])
async def get_available_characters(
    project_id: UUID,
    source_project_id: Optional[UUID] = Query(None, description="源项目 ID"),
    db: AsyncSession = Depends(get_db),
):
    """获取可以复制到目标项目的人物列表"""
    available = await CharacterService.get_available_characters_for_project(
        db=db,
        project_id=source_project_id,
        exclude_project_id=project_id,
    )
    return available


@router.post("/copy/{character_id}/to/{target_project_id}", response_model=CharacterResponse)
async def copy_character_to_project(
    character_id: UUID,
    target_project_id: UUID,
    copy_voice_profile: bool = Query(True, description="是否同时复制音色档案"),
    db: AsyncSession = Depends(get_db),
):
    """将人物复制到目标项目（跨集复用）"""
    new_character = await CharacterService.copy_character_to_project(
        db=db,
        source_character_id=character_id,
        target_project_id=target_project_id,
        copy_voice_profile=copy_voice_profile,
    )

    if not new_character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character {character_id} not found",
        )

    return new_character
