"""Initialize research database tables."""

import logging
from pathlib import Path

from sqlalchemy import text

logger = logging.getLogger(__name__)


async def init_research_database(project_id: str) -> None:
    """Initialize research database tables for a project.

    Args:
        project_id: Project ID.
    """
    from filmdub.core.orchestrator_db import get_database_manager
    from filmdub.workers.research import Base

    db = get_database_manager(project_id)
    await db.initialize()

    try:
        async with db.session() as session:
            # Create all research tables
            async with db.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info(f"Research database initialized for project {project_id}")

    except Exception as e:
        logger.error(f"Failed to initialize research database: {e}")
        raise
    finally:
        await db.close()


async def drop_research_tables(project_id: str) -> None:
    """Drop all research database tables for a project.

    Args:
        project_id: Project ID.
    """
    from filmdub.core.orchestrator_db import get_database_manager
    from filmdub.workers.research import Base

    db = get_database_manager(project_id)
    await db.initialize()

    try:
        async with db.session() as session:
            async with db.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

            logger.info(f"Research tables dropped for project {project_id}")

    except Exception as e:
        logger.error(f"Failed to drop research tables: {e}")
        raise
    finally:
        await db.close()
