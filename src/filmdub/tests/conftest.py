"""
Pytest 配置和 fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator

from src.filmdub.orchestrator.database import engine, Base, AsyncSessionLocal


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_database():
    """初始化测试数据库"""
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
