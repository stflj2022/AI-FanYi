"""Research API endpoints."""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from filmdub.core.config import settings
from filmdub.core.database import get_database_manager
from filmdub.workers.research.models import Character, Actor, Evidence, ResearchJob
from filmdub.workers.research.runner import ResearchWorker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}/research", tags=["research"])


class ResearchStartRequest(BaseModel):
    """Request to start research."""

    force: bool = False


class ResearchStatusResponse(BaseModel):
    """Research status response."""

    project_id: str
    status: str
    manifest_exists: bool
    episodes: int
    characters: int
    actors: int
    evidence: int
    sources: int
    confidence: dict[str, float]
    warnings: list[str]


class CharacterResponse(BaseModel):
    """Character response."""

    id: str
    canonical_name: str
    original_name: Optional[str]
    actor_id: Optional[str]
    character_type: Optional[str]
    description: Optional[str]
    confidence: float


class ActorResponse(BaseModel):
    """Actor response."""

    id: str
    canonical_name: str
    original_name: Optional[str]
    tmdb_id: Optional[int]
    wikidata_id: Optional[str]
    gender: Optional[str]
    birth_date: Optional[str]
    confidence: float


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def start_research(
    project_id: str,
    request: ResearchStartRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Start research for a project.

    Args:
        project_id: Project ID.
        request: Research start request.
        background_tasks: FastAPI background tasks.

    Returns:
        dict: Job ID.
    """
    # Validate project exists
    projects_dir = settings.projects_base_dir
    project_dir = projects_dir / project_id

    if not project_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}"
        )

    # Check media manifest exists
    media_manifest_path = project_dir / "manifests" / "media.json"
    if not media_manifest_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Media manifest not found. Please run Module 01 first."
        )

    # Load project manifest
    project_manifest_path = project_dir / "manifests" / "project.json"
    if not project_manifest_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project manifest not found."
        )

    with project_manifest_path.open("r") as f:
        project_manifest = json.load(f)

    # Start research in background
    async def run_research():
        """Run research in background."""
        worker = ResearchWorker(
            project_id=project_id,
            media_manifest_path=media_manifest_path,
            project_title=project_manifest["project"]["title"],
            duration=None,  # Will load from manifest
        )
        await worker.run()

    background_tasks.add_task(run_research)

    return {
        "message": "Research started",
        "project_id": project_id,
        "status": "QUEUED"
    }


@router.get("/status", response_model=ResearchStatusResponse)
async def get_research_status(project_id: str) -> ResearchStatusResponse:
    """Get research status for a project.

    Args:
        project_id: Project ID.

    Returns:
        ResearchStatusResponse: Research status.
    """
    projects_dir = settings.projects_base_dir
    project_dir = projects_dir / project_id
    manifest_path = project_dir / "research_manifest.json"

    if not manifest_path.exists():
        return ResearchStatusResponse(
            project_id=project_id,
            status="NOT_STARTED",
            manifest_exists=False,
            episodes=0,
            characters=0,
            actors=0,
            evidence=0,
            sources=0,
            confidence={},
            warnings=[],
        )

    # Load manifest
    with manifest_path.open("r") as f:
        manifest = json.load(f)

    return ResearchStatusResponse(
        project_id=project_id,
        status="COMPLETED",
        manifest_exists=True,
        episodes=1 if manifest.get("episode") else 0,
        characters=len(manifest.get("characters", [])),
        actors=len(manifest.get("actors", [])),
        evidence=manifest.get("evidence_count", 0),
        sources=manifest.get("sources_count", 0),
        confidence=manifest.get("confidence", {}),
        warnings=manifest.get("warnings", []),
    )


@router.get("/characters", response_model=list[CharacterResponse])
async def get_characters(project_id: str) -> list[CharacterResponse]:
    """Get characters for a project.

    Args:
        project_id: Project ID.

    Returns:
        list[CharacterResponse]: List of characters.
    """
    db = get_database_manager(project_id)
    await db.initialize()

    try:
        async with db.session() as session:
            from sqlalchemy import select

            stmt = select(Character).where(Character.project_id == project_id)
            result = await session.execute(stmt)
            characters = result.scalars().all()

            return [
                CharacterResponse(
                    id=char.id,
                    canonical_name=char.canonical_name,
                    original_name=char.original_name,
                    actor_id=char.actor_id,
                    character_type=char.character_type,
                    description=char.description,
                    confidence=char.confidence,
                )
                for char in characters
            ]
    finally:
        await db.close()


@router.get("/actors", response_model=list[ActorResponse])
async def get_actors(project_id: str) -> list[ActorResponse]:
    """Get actors for a project.

    Args:
        project_id: Project ID.

    Returns:
        list[ActorResponse]: List of actors.
    """
    db = get_database_manager(project_id)
    await db.initialize()

    try:
        async with db.session() as session:
            from sqlalchemy import select

            stmt = select(Actor).where(Actor.project_id == project_id)
            result = await session.execute(stmt)
            actors = result.scalars().all()

            return [
                ActorResponse(
                    id=actor.id,
                    canonical_name=actor.canonical_name,
                    original_name=actor.original_name,
                    tmdb_id=actor.tmdb_id,
                    wikidata_id=actor.wikidata_id,
                    gender=actor.gender,
                    birth_date=actor.birth_date,
                    confidence=actor.confidence,
                )
                for actor in actors
            ]
    finally:
        await db.close()


@router.get("/evidence")
async def get_evidence(
    project_id: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Get evidence for a project.

    Args:
        project_id: Project ID.
        entity_type: Filter by entity type.
        entity_id: Filter by entity ID.

    Returns:
        list[dict]: List of evidence.
    """
    db = get_database_manager(project_id)
    await db.initialize()

    try:
        async with db.session() as session:
            from sqlalchemy import select

            stmt = select(Evidence).where(Evidence.project_id == project_id)

            if entity_type:
                stmt = stmt.where(Evidence.entity_type == entity_type)
            if entity_id:
                stmt = stmt.where(Evidence.entity_id == entity_id)

            result = await session.execute(stmt)
            evidence_list = result.scalars().all()

            return [
                {
                    "id": ev.id,
                    "entity_type": ev.entity_type,
                    "entity_id": ev.entity_id,
                    "predicate": ev.predicate,
                    "value": ev.value,
                    "source_id": ev.source_id,
                    "confidence": ev.confidence,
                    "retrieved_at": ev.retrieved_at.isoformat(),
                }
                for ev in evidence_list
            ]
    finally:
        await db.close()


@router.get("/manifest")
async def get_manifest(project_id: str) -> dict[str, Any]:
    """Get research manifest.

    Args:
        project_id: Project ID.

    Returns:
        dict: Research manifest.
    """
    manifest_path = settings.projects_base_dir / project_id / "research_manifest.json"

    if not manifest_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research manifest not found"
        )

    with manifest_path.open("r") as f:
        return json.load(f)


@router.delete("")
async def reset_research(project_id: str) -> dict[str, str]:
    """Reset research data for a project.

    Args:
        project_id: Project ID.

    Returns:
        dict: Reset confirmation.
    """
    from workers.research.init_db import drop_research_tables

    # Drop tables
    await drop_research_tables(project_id)

    # Remove manifest
    manifest_path = settings.projects_base_dir / project_id / "research_manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()

    # Remove research directory
    research_dir = settings.projects_base_dir / project_id / "research"
    if research_dir.exists():
        import shutil
        shutil.rmtree(research_dir)

    return {
        "message": "Research data reset",
        "project_id": project_id,
    }
