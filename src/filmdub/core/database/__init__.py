"""Database connection and session management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from filmdub.core.config import settings

# Create Base for models
class Base(DeclarativeBase):
    """所有 SQLAlchemy 模型的基类"""
    pass


class DatabaseManager:
    """Manages database connections for projects."""

    def __init__(self, database_url: str | None = None):
        """Initialize database manager.

        Args:
            database_url: Database URL. If None, uses template from settings.
        """
        self._engine = None
        self._sessionmaker = None
        self._database_url = database_url

    async def initialize(self, database_url: str | None = None) -> None:
        """Initialize database engine and sessionmaker.

        Args:
            database_url: Optional override for database URL.
        """
        url = database_url or self._database_url
        if not url:
            raise ValueError("Database URL must be provided")

        self._engine = create_async_engine(
            url,
            echo=settings.log_level == "DEBUG",
            pool_pre_ping=True,
        )
        self._sessionmaker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a transactional scope around a series of operations.

        Yields:
            AsyncSession: Database session.
        """
        if self._sessionmaker is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self._sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @property
    def engine(self):
        """Get the database engine."""
        return self._engine


# Project-specific database managers cache
_database_managers: dict[str, DatabaseManager] = {}


def get_database_manager(project_id: str) -> DatabaseManager:
    """Get or create a database manager for a project.

    Args:
        project_id: Project ID.

    Returns:
        DatabaseManager: Database manager for the project.
    """
    if project_id not in _database_managers:
        url = settings.get_database_url(project_id)
        _database_managers[project_id] = DatabaseManager(url)
    return _database_managers[project_id]


async def close_all_databases() -> None:
    """Close all database connections."""
    for manager in _database_managers.values():
        await manager.close()
    _database_managers.clear()
