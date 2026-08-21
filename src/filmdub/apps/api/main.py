"""FastAPI main application."""

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from filmdub.core.config import settings
from filmdub.core.database import close_all_databases, get_database_manager
from filmdub.core.models import Episode, Job, JobEvent, MediaAsset, Project
from filmdub.core.schemas import (
    EpisodeCreate,
    EpisodeResponse,
    JobCreate,
    JobResponse,
    MediaResponse,
    ProjectCreate,
    ProjectResponse,
)
from filmdub.core.storage import StorageManager
from filmdub.workers.media_intake.probe import FFprobeError, FFprobeParser
from filmdub.workers.media_intake.runner import MediaIntakeWorker
from filmdub.apps.api import research, subtitle

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Yields:
        None
    """
    logger.info("Starting FilmDub API")
    yield
    logger.info("Shutting down FilmDub API")
    await close_all_databases()


app = FastAPI(
    title="FilmDub AI",
    description="A modular AI film dubbing system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(research.router)
app.include_router(subtitle.router)


# ==================== Health Check ====================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


# ==================== Projects ====================


@app.post("/api/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(project_data: ProjectCreate):
    """Create a new project.

    Args:
        project_data: Project creation data.

    Returns:
        ProjectResponse: Created project.
    """
    project_id = f"proj_{uuid.uuid4().hex[:12]}"

    # Initialize database
    db = get_database_manager(project_id)
    await db.initialize()

    try:
        async with db.session() as session:
            project = Project(
                id=project_id,
                title=project_data.title,
                original_title=project_data.original_title,
                target_language=project_data.target_language,
                status="CREATED",
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)

            # Create storage directories
            storage = StorageManager(project_id)
            storage.ensure_directories()

            # Save project manifest
            manifest = {
                "schema_version": "1.0",
                "project": {
                    "id": project.id,
                    "title": project.title,
                    "original_title": project.original_title,
                    "target_language": project.target_language,
                    "status": project.status,
                },
                "episodes": [],
            }
            storage.save_manifest("project", manifest)

            return ProjectResponse.model_validate(project)

    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        await db.close()


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get project by ID.

    Args:
        project_id: Project ID.

    Returns:
        ProjectResponse: Project details.
    """
    db = get_database_manager(project_id)
    await db.initialize()

    try:
        async with db.session() as session:
            project = await session.get(Project, project_id)
            if not project:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

            # Count episodes
            from sqlalchemy import select, func
            stmt = select(func.count()).select_from(Episode).where(Episode.project_id == project_id)
            result = await session.execute(stmt)
            episode_count = result.scalar() or 0

            response = ProjectResponse.model_validate(project)
            response.episode_count = episode_count
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        await db.close()


# ==================== Media Upload ====================


@app.post("/api/projects/{project_id}/media", response_model=MediaResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_media(
    project_id: str,
    file: UploadFile = File(..., description="Media file to upload"),
):
    """Upload media file to a project.

    Args:
        project_id: Project ID.
        file: Uploaded file.

    Returns:
        MediaResponse: Created media asset.
    """
    # Validate project exists
    db = get_database_manager(project_id)
    await db.initialize()

    try:
        async with db.session() as session:
            project = await session.get(Project, project_id)
            if not project:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check project: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        await db.close()

    # Save to temp location
    storage = StorageManager(project_id)
    temp_path = storage.get_temp_upload_path(f"{uuid.uuid4().hex}_{file.filename}")

    try:
        # Write uploaded file to temp location
        with temp_path.open("wb") as f:
            content = await file.read()
            f.write(content)

        # Run media intake worker
        worker = MediaIntakeWorker(
            project_id=project_id,
            media_path=temp_path,
            original_filename=file.filename or "unknown.mkv",
        )

        # Note: In production, this should run in a background task
        result = await worker.run()

        # Get created media
        await db.initialize()
        async with db.session() as session:
            media = await session.get(MediaAsset, result["media_id"])
            if not media:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create media record")

            response = MediaResponse.model_validate(media)

            # Load streams
            from sqlalchemy import select
            stmt = select(MediaStream).where(MediaStream.media_id == media.id)
            streams_result = await session.execute(stmt)
            response.streams = [MediaStreamResponse.model_validate(s) for s in streams_result.scalars()]

            return response

    except Exception as e:
        logger.error(f"Failed to upload media: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        # Cleanup temp file
        storage.cleanup_temp_file(temp_path)
        await db.close()


# ==================== Episodes ====================


@app.get("/api/episodes/{episode_id}", response_model=EpisodeResponse)
async def get_episode(episode_id: str):
    """Get episode by ID.

    Args:
        episode_id: Episode ID.

    Returns:
        EpisodeResponse: Episode details.
    """
    # Need to find project_id first from episode
    # For now, we'll search across databases
    # In production, maintain a central registry

    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not yet implemented")


# ==================== Jobs ====================


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get job by ID.

    Args:
        job_id: Job ID.

    Returns:
        JobResponse: Job details.
    """
    # Need to find project_id first
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not yet implemented")


@app.post("/api/jobs/{job_id}/retry", response_model=JobResponse)
async def retry_job(job_id: str):
    """Retry a failed job.

    Args:
        job_id: Job ID.

    Returns:
        JobResponse: Updated job.
    """
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not yet implemented")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "apps.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
