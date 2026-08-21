"""
Pytest 配置和 fixtures

统一从 `filmdub.*` 导入，避免 `src.filmdub` 命名空间包与 `filmdub`
产生两套独立的 Base/metadata 注册表（会导致建表与模型注册不一致）。
"""
import pytest
import asyncio
from typing import AsyncGenerator

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
