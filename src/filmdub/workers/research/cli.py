"""Research Worker - 命令行接口."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click

from filmdub.core.config import settings
from filmdub.core.database import get_database_manager
from filmdub.workers.research.init_db import init_research_database
from filmdub.workers.research.runner import ResearchWorker

logger = logging.getLogger(__name__)


@click.group()
def research():
    """Research management commands."""
    pass


@research.command("init")
@click.argument("project_id")
def init_research_db(project_id: str):
    """Initialize research database for a project.

    Args:
        project_id: Project ID.
    """
    asyncio.run(_init_research_db_impl(project_id))


async def _init_research_db_impl(project_id: str) -> None:
    """Implementation of research database initialization.

    Args:
        project_id: Project ID.
    """
    logger.info(f"Initializing research database for project {project_id}")

    try:
        await init_research_database(project_id)
        print(f"✓ Research database initialized for project {project_id}")
    except Exception as e:
        logger.error(f"Failed to initialize research database: {e}")
        print(f"✗ Failed to initialize research database: {e}")
        sys.exit(1)


@research.command("start")
@click.argument("project_id")
@click.option(
    "--force",
    is_flag=True,
    help="Force restart even if already completed"
)
def start_research(project_id: str, force: bool):
    """Start research for a project.

    Args:
        project_id: Project ID.
        force: Force restart.
    """
    asyncio.run(_start_research_impl(project_id, force))


async def _start_research_impl(project_id: str, force: bool) -> None:
    """Implementation of research start.

    Args:
        project_id: Project ID.
        force: Force restart.
    """
    logger.info(f"Starting research for project {project_id}")

    # Get paths
    projects_dir = settings.projects_base_dir
    project_dir = projects_dir / project_id
    media_manifest_path = project_dir / "manifests" / "media.json"

    if not media_manifest_path.exists():
        print(f"✗ Media manifest not found: {media_manifest_path}")
        print("Please run Module 01 first to create the media manifest.")
        return

    # Load project info
    import json
    project_manifest_path = project_dir / "manifests" / "project.json"
    with project_manifest_path.open("r") as f:
        project_manifest = json.load(f)

    project_title = project_manifest["project"]["title"]
    duration = None

    # Get duration from media manifest
    with media_manifest_path.open("r") as f:
        media_manifest = json.load(f)
        duration = media_manifest.get("container", {}).get("duration")

    print(f"Starting research for: {project_title}")
    print(f"  Project ID: {project_id}")
    print(f"  Duration: {duration}s" if duration else "Unknown")
    print()

    # Create and run worker
    worker = ResearchWorker(
        project_id=project_id,
        media_manifest_path=media_manifest_path,
        project_title=project_title,
        duration=duration,
    )

    try:
        result = await worker.run()

        print()
        print("✓ Research completed successfully!")
        print(f"  Job ID: {result['job_id']}")
        print(f"  Manifest: {result['manifest_path']}")

        if result.get('warnings'):
            print(f"\n⚠️  Warnings ({len(result['warnings'])}):")
            for warning in result['warnings']:
                print(f"    - {warning}")

        print(f"\n  Status: {result['status']}")
        print(f"  Project Status: READY_FOR_CHARACTERS")

    except Exception as e:
        print()
        print(f"✗ Research failed: {e}")
        logger.exception("Research failed")
        sys.exit(1)


@research.command("status")
@click.argument("project_id")
def research_status(project_id: str):
    """Show research status for a project.

    Args:
        project_id: Project ID.
    """
    print(f"Research Status for: {project_id}")

    # Check if manifest exists
    projects_dir = settings.projects_base_dir
    project_dir = projects_dir / project_id
    manifest_path = project_dir / "research_manifest.json"

    if manifest_path.exists():
        print("✓ Research manifest exists")
        import json
        with manifest_path.open("r") as f:
            manifest = json.load(f)

        print(f"\nProject: {manifest['project']['title']}")
        print(f"  Year: {manifest['project'].get('year', 'Unknown')}")
        print(f"  TMDB ID: {manifest['project'].get('tmdb_id', 'N/A')}")
        print(f"  Episodes: {1 if manifest.get('episode') else 0}")
        print(f"  Characters: {len(manifest.get('characters', []))}")
        print(f"  Actors: {len(manifest.get('actors', []))}")
        print(f"  Evidence: {manifest.get('evidence_count', 0)}")
        print(f"  Sources: {manifest.get('sources_count', 0)}")

        if manifest.get('episode'):
            ep = manifest['episode']
            print(f"\nEpisode:")
            print(f"  S{ep.get('season', '?'):02d}E{ep.get('episode', '?'):02d} - {ep.get('title', 'Unknown')}")

        if manifest.get('warnings'):
            print(f"\n⚠️  Warnings:")
            for warning in manifest.get('warnings', []):
                print(f"    - {warning}")

        print(f"\nConfidence:")
        for key, value in manifest.get('confidence', {}).items():
            print(f"  {key}: {value:.2f}")
    else:
        print("✗ No research manifest found")
        print("\nTo start research:")
        print(f"  python -m cli research start {project_id}")


@research.command("manifest")
@click.argument("project_id")
def show_manifest(project_id: str):
    """Show research manifest.

    Args:
        project_id: Project ID.
    """
    import json

    manifest_path = settings.projects_base_dir / project_id / "research_manifest.json"

    if manifest_path.exists():
        with manifest_path.open("r") as f:
            manifest = json.load(f)

        print(json.dumps(manifest, indent=2, ensure_ascii=False))
    else:
        print(f"No research manifest found for project {project_id}")


@research.command("reset")
@click.argument("project_id")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def reset_research(project_id: str, confirm: bool):
    """Reset research data for a project.

    Args:
        project_id: Project ID.
        confirm: Skip confirmation.
    """
    if not confirm:
        click.confirm(f"Are you sure you want to reset research data for project {project_id}?", abort=True)

    asyncio.run(_reset_research_impl(project_id))


async def _reset_research_impl(project_id: str) -> None:
    """Implementation of research reset."""
    logger.info(f"Resetting research data for project {project_id}")

    from filmdub.workers.research.init_db import drop_research_tables

    try:
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

        print(f"✓ Research data reset for project {project_id}")
    except Exception as e:
        logger.error(f"Failed to reset research data: {e}")
        print(f"✗ Failed to reset research data: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    research()
