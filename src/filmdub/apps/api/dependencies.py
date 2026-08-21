"""
依赖注入
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.filmdub.orchestrator.database import get_db


async def get_db_session() -> AsyncSession:
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
    async with get_db() as db:
        yield db
