"""
认证依赖注入和权限装饰器
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from filmdub.core.orchestrator_db import AsyncSessionLocal, get_db
from filmdub.apps.web.backend.services.auth_service import AuthService
from filmdub.apps.web.backend.models import User
from filmdub.apps.web.backend.api.schemas.auth_schemas import UserResponse


# HTTP Bearer 认证方案
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

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
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前管理员用户"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限",
        )
    return current_user


# 可选认证（不需要登录）
async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """可选认证（获取当前用户，未登录返回 None）"""
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
