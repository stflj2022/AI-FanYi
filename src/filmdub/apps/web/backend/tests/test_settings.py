"""设置管理测试"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.apps.web.backend.models import User
from filmdub.apps.web.backend.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_get_settings(async_client: AsyncClient, db_session: AsyncSession, test_user: User):
    """测试获取用户设置"""
    response = await async_client.get(
        "/api/v1/settings",
        headers={"Authorization": f"Bearer {await get_auth_token(async_client)}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email
    assert "settings" in data


@pytest.mark.asyncio
async def test_update_settings(async_client: AsyncClient, db_session: AsyncSession, test_user: User):
    """测试更新用户设置"""
    response = await async_client.put(
        "/api/v1/settings",
        json={
            "username": "newusername",
            "default_target_language": "en",
            "auto_start_jobs": True,
        },
        headers={"Authorization": f"Bearer {await get_auth_token(async_client)}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newusername"
    assert data["settings"]["default_target_language"] == "en"
    assert data["settings"]["auto_start_jobs"] is True


@pytest.mark.asyncio
async def test_change_password_success(async_client: AsyncClient, db_session: AsyncSession):
    """测试修改密码成功"""
    # 创建测试用户
    user = await AuthService.create_user(
        db=db_session,
        username="testuser2",
        email="test2@example.com",
        password="password123",
        is_admin=False,
    )

    # 修改密码
    response = await async_client.post(
        "/api/v1/settings/change-password",
        json={
            "old_password": "password123",
            "new_password": "newpassword456",
        },
        headers={"Authorization": f"Bearer {await get_auth_token(async_client, 'testuser2', 'password123')}"},
    )

    assert response.status_code == 204

    # 验证新密码可以登录
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "testuser2", "password": "newpassword456"},
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


@pytest.mark.asyncio
async def test_change_password_wrong_old_password(async_client: AsyncClient, db_session: AsyncSession, test_user: User):
    """测试修改密码时旧密码错误"""
    response = await async_client.post(
        "/api/v1/settings/change-password",
        json={
            "old_password": "wrongpassword",
            "new_password": "newpassword456",
        },
        headers={"Authorization": f"Bearer {await get_auth_token(async_client)}"},
    )

    assert response.status_code == 400
    assert "旧密码不正确" in response.json()["detail"]


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
