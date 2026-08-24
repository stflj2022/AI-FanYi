"""
认证依赖注入和权限装饰器

支持本地免登录模式（settings.auth_disabled）：
- AUTH_DISABLED=true 时所有需认证接口自动使用本地默认用户（local，管理员），无需登录
- 默认（auth_disabled=False）保持完整的 JWT 认证
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging

from filmdub.core.config import settings
from filmdub.core.orchestrator_db import AsyncSessionLocal, get_db
from filmdub.apps.web.backend.services.auth_service import AuthService
from filmdub.apps.web.backend.models import User
from filmdub.apps.web.backend.api.schemas.auth_schemas import UserResponse

logger = logging.getLogger(__name__)


# HTTP Bearer 认证方案（auto_error=False：本地免登录模式无 Token 也能进入依赖）
security = HTTPBearer(auto_error=False)


async def _get_or_create_local_user(db: AsyncSession) -> User:
    """
    本地免登录模式：获取或创建本地默认用户（管理员）

    密码使用随机生成值（创建时随即丢弃），确保关闭免登录开关后
    该账户无法通过密码登录（安全边界）。

    Returns:
        本地用户（username=local, is_admin=True）
    """
    import secrets

    user = await AuthService.get_user_by_username(db, "local")
    if user is None:
        user = await AuthService.create_user(
            db=db,
            username="local",
            email="local@local.local",
            password=secrets.token_urlsafe(32),
            is_admin=True,
        )
        logger.info("本地免登录模式：已创建本地默认用户 'local'（管理员，随机口令）")
    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前登录用户（本地免登录模式直接返回本地用户）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 本地免登录模式：不校验 Token，返回本地默认用户
    if settings.auth_disabled:
        return await _get_or_create_local_user(db)

    if credentials is None:
        raise credentials_exception

    # 解码 Token
    token = credentials.credentials
    payload = AuthService.decode_token(token)
    if payload is None:
        raise credentials_exception

    # 验证 Token 类型
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 Token 类型",
        )

    # 获取用户
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = await AuthService.get_user_by_id(db, uuid.UUID(user_id))
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户（本地免登录模式下本地用户即为活跃）"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前管理员用户（本地免登录模式下本地用户即为管理员，直接放行）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限",
        )
    return current_user


# 可选认证（不需要登录）
async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """可选认证（获取当前用户，未登录返回 None；本地免登录模式返回本地用户）"""
    if settings.auth_disabled:
        return await _get_or_create_local_user(db)

    if credentials is None:
        return None

    token = credentials.credentials
    payload = AuthService.decode_token(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    user = await AuthService.get_user_by_id(db, uuid.UUID(user_id))
    return user
