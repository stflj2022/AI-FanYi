"""
依赖注入
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.orchestrator.database import AsyncSessionLocal


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的依赖注入

    用于 FastAPI 依赖注入:

    ```python
    @app.get("/projects")
    async def get_projects(db: AsyncSession = Depends(get_db_session)):
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
