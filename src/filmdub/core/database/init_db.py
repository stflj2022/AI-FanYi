"""Database initialization utilities."""

import asyncio
from typing import Optional

from sqlalchemy import text

from core.config import settings
from core.database import get_database_manager
from core.models import Base, Episode, Job, JobEvent, MediaAsset, MediaStream, Project, SubtitleAsset


async def init_database(project_id: str) -> None:
    """Initialize database for a project, creating all tables if they don't exist.

    Args:
        project_id: Project ID.
    """
    db = get_database_manager(project_id)
    await db.initialize()

    # Use async connection to check and create tables
    async with db.engine.begin() as conn:
        # Check if projects table exists
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
        )
        projects_exists = result.fetchone() is not None

        if not projects_exists:
            # Create all tables using SQLAlchemy
            # Create tables one by one to handle index errors gracefully
            for table in Base.metadata.sorted_tables:
                try:
                    await conn.run_sync(table.create, checkfirst=True)
                except Exception as e:
                    # Ignore "already exists" errors for indexes
                    if "already exists" not in str(e):
                        raise
            print(f"✓ Database tables created for project {project_id}")
        else:
            # Verify all required tables exist
            required_tables = [
                'projects', 'episodes', 'media_assets', 'media_streams',
                'subtitle_assets', 'jobs', 'job_events'
            ]
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            existing_tables = {row[0] for row in result.fetchall()}

            missing_tables = set(required_tables) - existing_tables
            if missing_tables:
                # Create missing tables
                for table_name in missing_tables:
                    # Get the table object
                    table = Base.metadata.tables.get(table_name)
                    if table:
                        await conn.run_sync(table.create, checkfirst=True)
                        print(f"✓ Created missing table: {table_name}")

            print(f"✓ Database verified for project {project_id}")


async def drop_database(project_id: str) -> None:
    """Drop all tables for a project (DESTRUCTIVE!).

    Args:
        project_id: Project ID.
    """
    db = get_database_manager(project_id)
    await db.initialize()

    try:
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print(f"✓ Database dropped for project {project_id}")
    finally:
        await db.close()


async def reset_database(project_id: str) -> None:
    """Reset database for a project (drop and recreate).

    Args:
        project_id: Project ID.
    """
    await drop_database(project_id)
    await init_database(project_id)


# Command-line interface
if __name__ == "__main__":
    import sys

    async def main():
        if len(sys.argv) < 2:
            print("Usage: python init_db.py <project_id> [init|drop|reset]")
            sys.exit(1)

        project_id = sys.argv[1]
        action = sys.argv[2] if len(sys.argv) > 2 else "init"

        if action == "init":
            await init_database(project_id)
        elif action == "drop":
            await drop_database(project_id)
        elif action == "reset":
            await reset_database(project_id)
        else:
            print(f"Unknown action: {action}")
            sys.exit(1)

    asyncio.run(main())
