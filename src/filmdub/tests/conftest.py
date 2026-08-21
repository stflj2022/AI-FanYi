"""
Pytest 配置和 fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator

try:
    from src.filmdub.orchestrator.database import engine, Base, AsyncSessionLocal
except ImportError:
    from filmdub.orchestrator.database import engine, Base, AsyncSessionLocal


@pytest.fixture(scope="session")
def event_loop_policy():
    """创建事件循环策略"""
    policy = asyncio.get_event_loop_policy()
    yield policy


@pytest.fixture(scope="function", autouse=True)
async def setup_database():
    """初始化测试数据库（每个测试函数自动执行）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db(setup_database) -> AsyncGenerator:
    """提供数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
