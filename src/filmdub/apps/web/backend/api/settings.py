"""设置 API 端点"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.core.orchestrator_db import get_db_context
from filmdub.apps.web.backend.models import User
from filmdub.apps.web.backend.api.dependencies import get_current_active_user
from filmdub.apps.web.backend.api.schemas.settings_schemas import (
    UserSettingsUpdate,
    ChangePasswordRequest,
    UserSettingsResponse,
)
from filmdub.apps.web.backend.services.auth_service import AuthService

router = APIRouter()


@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_active_user),
):
    """获取当前用户设置"""
    return UserSettingsResponse.model_validate(current_user)


@router.put("", response_model=UserSettingsResponse)
async def update_settings(
    settings_data: UserSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_context),
):
    """更新用户设置"""
    from datetime import datetime

    # 更新个人信息
    if settings_data.username is not None:
        current_user.username = settings_data.username
    if settings_data.email is not None:
        current_user.email = settings_data.email

    # 更新设置
    update_data = settings_data.model_dump(exclude_unset=True, exclude={'username', 'email'})
    if update_data:
        current_user.settings = {**current_user.settings, **update_data}

    current_user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(current_user)

    return UserSettingsResponse.model_validate(current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_context),
):
    """修改密码"""
    # 验证旧密码
    if not AuthService.verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码不正确",
        )

    # 更新密码
    current_user.password_hash = AuthService.hash_password(password_data.new_password)
    await db.commit()
