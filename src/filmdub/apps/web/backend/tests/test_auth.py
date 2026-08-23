"""认证相关测试"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from filmdub.apps.web.backend.models import User
from filmdub.apps.web.backend.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_register_success(async_client: AsyncClient, db_session: AsyncSession):
    """测试用户注册成功"""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert data["is_active"] is True
    assert data["is_admin"] is False

    # 验证用户已创建
    result = await db_session.execute(
        select(User).where(User.username == "testuser")
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.email == "test@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_username(async_client: AsyncClient, db_session: AsyncSession):
    """测试注册重复用户名"""
    # 先创建一个用户
    user = User(
        username="existinguser",
        email="existing@example.com",
        password_hash=AuthService.hash_password("password123"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    # 尝试注册相同用户名
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "existinguser",
            "email": "different@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )

    assert response.status_code == 400
    assert "用户名已被占用" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient, db_session: AsyncSession):
    """测试注册重复邮箱"""
    # 先创建一个用户
    user = User(
        username="user1",
        email="shared@example.com",
        password_hash=AuthService.hash_password("password123"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    # 尝试注册相同邮箱
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "user2",
            "email": "shared@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )

    assert response.status_code == 400
    assert "邮箱已被注册" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_password_mismatch(async_client: AsyncClient):
    """测试密码不匹配"""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
            "confirm_password": "different123",
        },
    )

    assert response.status_code == 422  # Pydantic 验证错误


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, db_session: AsyncSession):
    """测试登录成功"""
    # 先创建一个用户
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=AuthService.hash_password("password123"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    # 登录
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 86400  # 24 小时
    assert data["user"]["username"] == "testuser"


@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient, db_session: AsyncSession):
    """测试密码错误"""
    # 先创建一个用户
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=AuthService.hash_password("password123"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    # 错误密码登录
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    assert "用户名或密码错误" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_user_not_found(async_client: AsyncClient):
    """测试用户不存在"""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": "nonexistent",
            "password": "password123",
        },
    )

    assert response.status_code == 401
    assert "用户名或密码错误" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user(async_client: AsyncClient, db_session: AsyncSession):
    """测试获取当前用户信息"""
    # 先创建一个用户
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=AuthService.hash_password("password123"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    # 登录获取 token
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "password123",
        },
    )
    token = login_response.json()["access_token"]

    # 获取当前用户信息
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_refresh_token(async_client: AsyncClient, db_session: AsyncSession):
    """测试刷新 Token"""
    # 先创建一个用户
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=AuthService.hash_password("password123"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    # 登录获取 tokens
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "password123",
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    # 刷新 token
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["username"] == "testuser"


@pytest.mark.asyncio
async def test_unauthorized_request(async_client: AsyncClient):
    """测试未授权请求"""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(async_client: AsyncClient, db_session: AsyncSession):
    """测试登出"""
    # 先创建一个用户
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=AuthService.hash_password("password123"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    # 登录获取 token
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "password123",
        },
    )
    token = login_response.json()["access_token"]

    # 登出
    response = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "登出成功"


# @pytest.mark.asyncio
# async def test_password_hashing():
#     """测试密码哈希和验证"""
#     plain_password = "test_password_123"
#
#     # 哈希密码
#     hashed = AuthService.hash_password(plain_password)
#     assert hashed != plain_password
#     assert len(hashed) > 0
#
#     # 验证正确密码
#     assert AuthService.verify_password(plain_password, hashed) is True
#
#     # 验证错误密码
#     assert AuthService.verify_password("wrong_password", hashed) is False
#
# TODO: 修复 bcrypt 库版本兼容性问题后恢复此测试
