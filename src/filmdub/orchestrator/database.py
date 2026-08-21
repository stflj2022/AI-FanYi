"""
Layer 0 Orchestrator 数据库连接和会话管理
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import orchestrator_settings


# 创建异步引擎
engine = create_async_engine(
    orchestrator_settings.database_url,
    echo=orchestrator_settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """所有 SQLAlchemy 模型的基类"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的依赖注入函数

    用于 FastAPI 依赖注入:

    ```python
    @app.get("/projects")
    async def get_projects(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Project))
        return result.scalars().all()
    ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的上下文管理器

    用于在非 FastAPI 环境中使用:

    ```python
    async with get_db_context() as db:
        result = await db.execute(select(Project))
        projects = result.scalars().all()
    ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    初始化数据库（创建所有表）

    注意: 生产环境应该使用 Alembic 迁移
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库连接"""
    await engine.dispose()
