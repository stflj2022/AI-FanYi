"""系统状态测试"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.apps.web.backend.models import User
from filmdub.apps.web.backend.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_get_system_status_as_admin(async_client: AsyncClient, db_session: AsyncSession, admin_user: User):
    """测试管理员获取系统状态"""
    response = await async_client.get(
        "/api/v1/system/status",
        headers={"Authorization": f"Bearer {await get_auth_token(async_client, 'admin', 'admin123')}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "uptime" in data
    assert "resources" in data
    assert "workers" in data
    assert "queue" in data
    assert "modules" in data


@pytest.mark.asyncio
async def test_get_system_status_as_user(async_client: AsyncClient, db_session: AsyncSession, test_user: User):
    """测试普通用户获取系统状态（应该被拒绝）"""
    response = await async_client.get(
        "/api/v1/system/status",
        headers={"Authorization": f"Bearer {await get_auth_token(async_client)}"},
    )

    assert response.status_code == 403
    assert "需要管理员权限" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_workers_as_admin(async_client: AsyncClient, db_session: AsyncSession, admin_user: User):
    """测试管理员获取 Worker 状态"""
    response = await async_client.get(
        "/api/v1/system/workers",
        headers={"Authorization": f"Bearer {await get_auth_token(async_client, 'admin', 'admin123')}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_queue_as_admin(async_client: AsyncClient, db_session: AsyncSession, admin_user: User):
    """测试管理员获取队列状态"""
    response = await async_client.get(
        "/api/v1/system/queue",
        headers={"Authorization": f"Bearer {await get_auth_token(async_client, 'admin', 'admin123')}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "pending" in data
    assert "running" in data
    assert "completed" in data
    assert "failed" in data
    assert "total" in data


async def get_auth_token(async_client: AsyncClient, username: str = "testuser", password: str = "password123") -> str:
    """获取认证 token 的辅助函数"""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    return response.json()["access_token"]


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用户"""
    from filmdub.apps.web.backend.services.auth_service import AuthService

    user = await AuthService.create_user(
        db=db_session,
        username="testuser",
        email="test@example.com",
        password="password123",
        is_admin=False,
    )
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """创建管理员用户"""
    from filmdub.apps.web.backend.services.auth_service import AuthService

    user = await AuthService.create_user(
        db=db_session,
        username="admin",
        email="admin@example.com",
        password="admin123",
        is_admin=True,
    )
    return user
