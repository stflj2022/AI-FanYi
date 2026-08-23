"""Command-line interface for FilmDub AI."""

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from filmdub.core.config import settings
from filmdub.core.database import get_database_manager
from filmdub.core.database.init_db import init_database
from filmdub.core.models import Episode, Job, MediaAsset, Project
from filmdub.core.storage import StorageManager
from filmdub.workers.media_intake.runner import MediaIntakeWorker
from filmdub.workers.research.cli import research as research_cli
from filmdub.workers.subtitle.cli import subtitle as subtitle_cli

load_dotenv()

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """FilmDub AI - A modular AI film dubbing system."""
    pass


@cli.group()
def project():
    """Project management commands."""
    pass


@project.command("create")
@click.option("--title", required=True, help="Project title")
@click.option("--original-title", help="Original title in source language")
@click.option("--target-language", default="zh-CN", help="Target language code (e.g., zh-CN)")
def create_project(title: str, original_title: Optional[str], target_language: str):
    """Create a new project.

    Args:
        title: Project title.
        original_title: Original title.
        target_language: Target language code.
    """
    asyncio.run(_create_project_impl(title, original_title, target_language))


async def _create_project_impl(title: str, original_title: Optional[str], target_language: str) -> None:
    """Implementation of project creation.

    Args:
        title: Project title.
        original_title: Original title.
        target_language: Target language code.
    """
    project_id = f"proj_{uuid.uuid4().hex[:12]}"

    logger.info(f"Creating project: {title}")
    logger.info(f"Project ID: {project_id}")

    # Create storage directories first
    storage = StorageManager(project_id)
    storage.ensure_directories()

    # Initialize database
    await init_database(project_id)

    db = get_database_manager(project_id)

    try:
        async with db.session() as session:

            # Create project
            project = Project(
                id=project_id,
                title=title,
                original_title=original_title,
                target_language=target_language,
                status="CREATED",
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)

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

        click.echo(f"✓ Project created successfully!")
        click.echo(f"  Project ID: {project_id}")
        click.echo(f"  Title: {project.title}")
        click.echo(f"  Target Language: {project.target_language}")
        click.echo(f"  Status: {project.status}")

    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        click.echo(f"✗ Failed to create project: {e}", err=True)
        raise
    finally:
        await db.close()


@project.command("list")
def list_projects():
    """List all projects."""
    projects_dir = settings.projects_base_dir

    if not projects_dir.exists():
        click.echo("No projects found.")
        return

    projects = [d for d in projects_dir.iterdir() if d.is_dir() and d.name.startswith("proj_")]

    if not projects:
        click.echo("No projects found.")
        return

    click.echo(f"Found {len(projects)} project(s):\n")

    for proj_dir in sorted(projects):
        project_id = proj_dir.name
        manifest_path = proj_dir / "manifests" / "project.json"

        if manifest_path.exists():
            with manifest_path.open("r") as f:
                manifest = json.load(f)
                project_info = manifest.get("project", {})
                click.echo(f"  {project_id}")
                click.echo(f"    Title: {project_info.get('title', 'N/A')}")
                click.echo(f"    Status: {project_info.get('status', 'N/A')}")
                click.echo(f"    Target: {project_info.get('target_language', 'N/A')}")
                click.echo()


@project.command("info")
@click.argument("project_id")
def project_info(project_id: str):
    """Show project information.

    Args:
        project_id: Project ID.
    """
    asyncio.run(_project_info_impl(project_id))


async def _project_info_impl(project_id: str) -> None:
    """Implementation of project info."""
    db = get_database_manager(project_id)
    await db.initialize()

    try:
        async with db.session() as session:
            project = await session.get(Project, project_id)
            if not project:
                click.echo(f"✗ Project not found: {project_id}", err=True)
                return

            click.echo(f"Project ID: {project.id}")
            click.echo(f"Title: {project.title}")
            if project.original_title:
                click.echo(f"Original Title: {project.original_title}")
            click.echo(f"Target Language: {project.target_language}")
            click.echo(f"Status: {project.status}")
            click.echo(f"Created: {project.created_at}")
            click.echo(f"Updated: {project.updated_at}")

            # Count episodes
            from sqlalchemy import select, func
            stmt = select(func.count()).select_from(Episode).where(Episode.project_id == project_id)
            result = await session.execute(stmt)
            episode_count = result.scalar() or 0
            click.echo(f"Episodes: {episode_count}")

            # Count media
            stmt = select(func.count()).select_from(MediaAsset).join(Episode).where(Episode.project_id == project_id)
            result = await session.execute(stmt)
            media_count = result.scalar() or 0
            click.echo(f"Media Files: {media_count}")

            # Count jobs
            stmt = select(func.count()).select_from(Job).where(Job.project_id == project_id)
            result = await session.execute(stmt)
            job_count = result.scalar() or 0
            click.echo(f"Jobs: {job_count}")

    except Exception as e:
        logger.error(f"Failed to get project info: {e}")
        click.echo(f"✗ Failed to get project info: {e}", err=True)
    finally:
        await db.close()


@cli.group()
def media():
    """Media management commands."""
    pass


@media.command("import")
@click.argument("project_id")
@click.argument("media_path", type=click.Path(exists=True))
def import_media(project_id: str, media_path: str):
    """Import media file to a project.

    Args:
        project_id: Project ID.
        media_path: Path to media file.
    """
    asyncio.run(_import_media_impl(project_id, media_path))


async def _import_media_impl(project_id: str, media_path: str) -> None:
    """Implementation of media import."""
    media_file = Path(media_path)

    if not media_file.exists():
        click.echo(f"✗ File not found: {media_path}", err=True)
        return

    click.echo(f"Importing media: {media_file.name}")
    click.echo(f"Project ID: {project_id}")

    # Run worker
    worker = MediaIntakeWorker(
        project_id=project_id,
        media_path=media_file,
        original_filename=media_file.name,
    )

    try:
        result = await worker.run()

        click.echo(f"\n✓ Media imported successfully!")
        click.echo(f"  Job ID: {result['job_id']}")
        click.echo(f"  Episode ID: {result['episode_id']}")
        click.echo(f"  Media ID: {result['media_id']}")

        # Show media info
        db = get_database_manager(project_id)
        await db.initialize()

        try:
            async with db.session() as session:
                media = await session.get(MediaAsset, result["media_id"])
                if media:
                    click.echo(f"\n  File: {media.original_filename}")
                    click.echo(f"  Size: {media.file_size / (1024**3):.2f} GB")
                    click.echo(f"  Duration: {media.duration_seconds:.1f} seconds")
                    click.echo(f"  Container: {media.container_format}")
                    click.echo(f"  SHA256: {media.sha256[:32]}...")
        finally:
            await db.close()

    except Exception as e:
        logger.error(f"Failed to import media: {e}")
        click.echo(f"\n✗ Failed to import media: {e}", err=True)
        raise


@media.command("inspect")
@click.argument("project_id")
@click.argument("media_id")
def inspect_media(project_id: str, media_id: str):
    """Inspect media asset details.

    Args:
        project_id: Project ID.
        media_id: Media ID.
    """
    asyncio.run(_inspect_media_impl(project_id, media_id))


async def _inspect_media_impl(project_id: str, media_id: str) -> None:
    """Implementation of media inspect."""
    db = get_database_manager(project_id)
    await db.initialize()

    try:
        async with db.session() as session:
            media = await session.get(MediaAsset, media_id)
            if not media:
                click.echo(f"✗ Media not found: {media_id}", err=True)
                return

            click.echo(f"Media ID: {media.id}")
            click.echo(f"Filename: {media.original_filename}")
            click.echo(f"Size: {media.file_size / (1024**3):.2f} GB")
            click.echo(f"Duration: {media.duration_seconds:.1f} seconds")
            click.echo(f"Container: {media.container_format}")
            click.echo(f"SHA256: {media.sha256}")
            click.echo(f"Status: {media.status}")
            click.echo(f"Created: {media.created_at}")

            # Load manifest
            storage = StorageManager(project_id)
            manifest = storage.load_manifest("media")
            if manifest:
                click.echo("\nVideo Stream:")
                video = manifest.get("video", {})
                if video:
                    click.echo(f"  Codec: {video.get('codec')}")
                    click.echo(f"  Resolution: {video.get('width')}x{video.get('height')}")
                    click.echo(f"  FPS: {video.get('fps')}")

                click.echo("\nAudio Streams:")
                for i, audio in enumerate(manifest.get("audio", []), 1):
                    click.echo(f"  [{i}] {audio.get('language', 'unknown')} - {audio.get('codec')}")
                    click.echo(f"      Channels: {audio.get('channels')}, Sample Rate: {audio.get('sample_rate')} Hz")

                click.echo("\nSubtitle Streams:")
                for i, sub in enumerate(manifest.get("subtitles", []), 1):
                    click.echo(f"  [{i}] {sub.get('language', 'unknown')} - {sub.get('codec')}")

    except Exception as e:
        logger.error(f"Failed to inspect media: {e}")
        click.echo(f"✗ Failed to inspect media: {e}", err=True)
    finally:
        await db.close()


@cli.group()
def job():
    """Job management commands."""
    pass


@job.command("status")
@click.argument("project_id")
@click.argument("job_id")
def job_status(project_id: str, job_id: str):
    """Show job status.

    Args:
        project_id: Project ID.
        job_id: Job ID.
    """
    asyncio.run(_job_status_impl(project_id, job_id))


async def _job_status_impl(project_id: str, job_id: str) -> None:
    """Implementation of job status."""
    db = get_database_manager(project_id)
    await db.initialize()

    try:
        async with db.session() as session:
            job = await session.get(Job, job_id)
            if not job:
                click.echo(f"✗ Job not found: {job_id}", err=True)
                return

            click.echo(f"Job ID: {job.id}")
            click.echo(f"Module: {job.module}")
            click.echo(f"Status: {job.status}")
            click.echo(f"Attempt: {job.attempt}")
            click.echo(f"Started: {job.started_at}")
            click.echo(f"Finished: {job.finished_at}")

            if job.error_code:
                click.echo(f"Error Code: {job.error_code}")
            if job.error_message:
                click.echo(f"Error: {job.error_message}")

    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        click.echo(f"✗ Failed to get job status: {e}", err=True)
    finally:
        await db.close()


def main():
    """Main entry point."""
    # Add subcommands
    cli.add_command(research_cli, name="research")
    cli.add_command(subtitle_cli, name="subtitle")
    cli()


if __name__ == "__main__":
    main()
