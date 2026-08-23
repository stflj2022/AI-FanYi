"""项目管理测试"""
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from filmdub.apps.web.backend.models import User
from filmdub.core.models import WebProject as ProjectRecord, ProjectStatus
from filmdub.apps.web.backend.services.project_service import ProjectService


@pytest.mark.asyncio
async def test_create_project(async_client: AsyncClient, db_session: AsyncSession, test_user: User):
    """测试创建项目"""
    response = await async_client.post(
        "/api/v1/projects",
        json={
            "name": "Test Project",
            "description": "Test Description",
            "title": "Test Title",
            "target_language": "zh",
        },
        headers={"Authorization": f"Bearer {await get_auth_token(async_client)}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["description"] == "Test Description"
    assert data["title"] == "Test Title"
    assert data["target_language"] == "zh"


@pytest.mark.asyncio
async def test_list_projects(async_client: AsyncClient, db_session: AsyncSession, test_user: User):
    """测试获取项目列表"""
    # 创建测试项目
    for i in range(3):
        project = ProjectRecord(
            name=f"Project {i}",
            description=f"Description {i}",
            target_language="zh",
            created_by=test_user.id,
            status=ProjectStatus.PENDING,
        )
        db_session.add(project)
    await db_session.commit()

    # 获取项目列表
    response = await async_client.get(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {await get_auth_token(async_client)}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3


@pytest.mark.asyncio
async def test_get_project(async_client: AsyncClient, db_session: AsyncSession, test_user: User):
    """测试获取项目详情"""
    # 创建测试项目
    project = ProjectRecord(
        name="Test Project",
        description="Test Description",
        target_language="zh",
        created_by=test_user.id,
        status=ProjectStatus.PENDING,
    )
    db_session.add(project)
    await db_session.commit()

    # 获取项目详情
    response = await async_client.get(
        f"/api/v1/projects/{project.id}",
        headers={"Authorization": f"Bearer {await get_auth_token(async_client)}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Project"


@pytest.mark.asyncio
async def test_update_project(async_client: AsyncClient, db_session: AsyncSession, test_user: User):
    """测试更新项目"""
    # 创建测试项目
    project = ProjectRecord(
        name="Test Project",
        description="Test Description",
        target_language="zh",
        created_by=test_user.id,
        status=ProjectStatus.PENDING,
    )
    db_session.add(project)
    await db_session.commit()

    # 更新项目
    response = await async_client.put(
        f"/api/v1/projects/{project.id}",
        json={"name": "Updated Project", "description": "Updated Description"},
        headers={"Authorization": f"Bearer {await get_auth_token(async_client)}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Project"


@pytest.mark.asyncio
async def test_delete_project(async_client: AsyncClient, db_session: AsyncSession, test_user: User):
    """测试删除项目"""
    # 创建测试项目
    project = ProjectRecord(
        name="Test Project",
        description="Test Description",
        target_language="zh",
        created_by=test_user.id,
        status=ProjectStatus.PENDING,
    )
    db_session.add(project)
    await db_session.commit()

    # 删除项目
    response = await async_client.delete(
        f"/api/v1/projects/{project.id}",
        headers={"Authorization": f"Bearer {await get_auth_token(async_client)}"},
    )

    assert response.status_code == 204

    # 验证项目已删除
    result = await db_session.execute(select(ProjectRecord).where(ProjectRecord.id == project.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_project_permission(async_client: AsyncClient, db_session: AsyncSession):
    """测试项目权限"""
    from filmdub.apps.web.backend.services.auth_service import AuthService

    # 创建两个用户
    user1 = await AuthService.create_user(
        db=db_session,
        username="user1",
        email="user1@example.com",
        password="password123",
        is_admin=False,
    )
    user2 = await AuthService.create_user(
        db=db_session,
        username="user2",
        email="user2@example.com",
        password="password123",
        is_admin=False,
    )

    # 创建属于 user1 的项目
    project = ProjectRecord(
        name="User1 Project",
        description="Project owned by user1",
        target_language="zh",
        created_by=user1.id,
        status=ProjectStatus.PENDING,
    )
    db_session.add(project)
    await db_session.commit()

    # user2 尝试访问 user1 的项目
    token2 = await get_auth_token(async_client, "user2", "password123")
    response = await async_client.get(
        f"/api/v1/projects/{project.id}",
        headers={"Authorization": f"Bearer {token2}"},
    )

    assert response.status_code == 404


async def get_auth_token(async_client: AsyncClient, username: str = "testuser", password: str = "password123") -> str:
    """获取认证 token 的辅助函数"""
    # 确保用户存在
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
