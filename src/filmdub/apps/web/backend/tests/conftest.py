"""测试配置和 fixtures"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator

from filmdub.apps.web.backend.main import app
from filmdub.apps.web.backend.models import User, Base, Project, Character, Job
from filmdub.core.orchestrator_db import get_db_context
from filmdub.apps.web.backend.services.auth_service import AuthService


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
        from filmdub.apps.web.backend.models import User, Project, Character, Job
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
    app.dependency_overrides[orchestrator_db.get_db_context] = override_get_db

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
