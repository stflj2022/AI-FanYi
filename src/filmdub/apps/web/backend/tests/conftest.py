"""测试配置和 fixtures"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator

from filmdub.apps.web.backend.main import app
from filmdub.apps.web.backend.models import User, Base
from filmdub.core.models import ProjectRecord as Project, Character, Job
from filmdub.core.orchestrator_db import get_db
from filmdub.apps.web.backend.services.auth_service import AuthService
from filmdub.core.config import settings


@pytest.fixture(autouse=True)
def _default_auth_enabled(monkeypatch):
    """测试默认非本地免登录模式（不受 .env 的 AUTH_DISABLED 影响），需要本地模式的测试自行开启"""
    monkeypatch.setattr(settings, "auth_disabled", False)
    yield


# 测试数据库配置
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    # 创建表
    async with test_engine.begin() as conn:
        # 导入所有模型以确保表被创建
        from filmdub.apps.web.backend.models import User
        from filmdub.core.models import ProjectRecord, Character, Job
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    # 清理
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """创建异步测试客户端"""

    async def override_get_db():
        yield db_session

    # 覆盖数据库依赖
    from filmdub.core import orchestrator_db
    app.dependency_overrides[orchestrator_db.get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # 清理依赖覆盖
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用户"""
    user = await AuthService.create_user(
        db=db_session,
        username="testuser",
        email="test@example.com",
        password="password123",
        is_admin=False,
    )
    return user


@pytest.fixture(scope="function")
async def auth_headers(test_user: User) -> dict:
    """创建认证 headers"""
    token = AuthService.create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
async def test_project(db_session: AsyncSession, test_user: User) -> Project:
    """创建测试项目"""
    project = Project(
        title="测试项目",
        description="这是一个测试项目",
        source_language="en",
        target_language="zh",
        created_by=test_user.id,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project
