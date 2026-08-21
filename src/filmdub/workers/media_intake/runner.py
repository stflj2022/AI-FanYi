"""Media Intake Worker - Main runner."""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import settings
from core.database import get_database_manager
from core.models import (
    Episode,
    Job,
    JobEvent,
    MediaAsset,
    MediaStream,
    Project,
    SubtitleAsset,
)
from core.storage import StorageManager
from workers.media_intake.filename_parser import FilenameParseResult, parse_filename, sanitize_filename
from workers.media_intake.hashing import compute_sha256
from workers.media_intake.manifest import build_media_manifest
from workers.media_intake.probe import FFprobeError, FFprobeParser
from workers.media_intake.validator import MediaValidationError, MediaValidator

logger = logging.getLogger(__name__)


class MediaIntakeError(Exception):
    """Media intake worker error."""

    pass


class MediaIntakeWorker:
    """Worker for processing media intake jobs."""

    def __init__(self, project_id: str, media_path: Path, original_filename: str):
        """Initialize media intake worker.

        Args:
            project_id: Project ID.
            media_path: Path to media file.
            original_filename: Original filename.
        """
        self.project_id = project_id
        self.media_path = media_path
        self.original_filename = sanitize_filename(original_filename)
        self.job_id = f"job_{uuid.uuid4().hex[:12]}"

        # Initialize components
        self.storage = StorageManager(project_id)
        self.parser = FFprobeParser()
        self.validator = MediaValidator(max_file_size=int(settings.upload_max_file_size_gb * 1024 ** 3))

        # Results
        self.media_id: Optional[str] = None
        self.episode_id: Optional[str] = None
        self.probe_data: Optional[dict] = None
        self.sha256: Optional[str] = None
        self.file_size: Optional[int] = None
        self.duration: Optional[float] = None
        self.filename_parse: Optional[FilenameParseResult] = None

    async def run(self) -> dict:
        """Run media intake process.

        Returns:
            dict: Result summary.

        Raises:
            MediaIntakeError: If process fails.
        """
        logger.info(f"Starting media intake for project {self.project_id}")

        # Initialize database
        db = get_database_manager(self.project_id)
        await db.initialize()

        try:
            # Create job
            job = await self._create_job(db)

            # Process media
            await self._process_media(db, job)

            # Update project status
            await self._update_project_status(db)

            logger.info(f"Media intake completed successfully: {self.media_id}")

            return {
                "job_id": self.job_id,
                "project_id": self.project_id,
                "episode_id": self.episode_id,
                "media_id": self.media_id,
                "status": "SUCCESS",
            }

        except Exception as e:
            logger.error(f"Media intake failed: {e}")
            await self._fail_job(db, str(e))
            raise MediaIntakeError(f"Media intake failed: {e}") from e
        finally:
            await db.close()

    async def _create_job(self, db) -> Job:
        """Create job record.

        Args:
            db: Database manager.

        Returns:
            Job: Created job.
        """
        async with db.session() as session:
            job = Job(
                id=self.job_id,
                project_id=self.project_id,
                module="media_intake",
                status="RUNNING",
                attempt=1,
                started_at=datetime.utcnow(),
            )
            session.add(job)

            # Log start event
            event = JobEvent(
                job_id=self.job_id,
                level="INFO",
                event_type="JOB_STARTED",
                message=f"Media intake started for {self.original_filename}",
            )
            session.add(event)

            await session.commit()
            await session.refresh(job)

        return job

    async def _process_media(self, db, job: Job) -> None:
        """Process media file.

        Args:
            db: Database manager.
            job: Job record.
        """
        # Log file validation
        await self._log_event(db, "INFO", "FILE_VALIDATION_STARTED", "Validating media file")

        # Run FFprobe first
        await self._log_event(db, "INFO", "FFPROBE_STARTED", "Running FFprobe analysis")
        self.probe_data = self.parser.probe(self.media_path)
        await self._log_event(db, "INFO", "FFPROBE_COMPLETED", "FFprobe analysis completed")

        # Validate file and probe
        self.file_size, self.duration = self.validator.validate_all(
            self.media_path,
            self.probe_data
        )

        # Generate IDs
        self.media_id = f"med_{uuid.uuid4().hex[:12]}"
        self.episode_id = f"ep_{uuid.uuid4().hex[:12]}"

        # Compute hash
        await self._log_event(db, "INFO", "HASHING_STARTED", "Computing SHA-256 hash")
        self.sha256 = compute_sha256(self.media_path)
        await self._log_event(db, "INFO", "HASHING_COMPLETED", f"SHA-256: {self.sha256[:16]}...")

        # Parse filename
        self.filename_parse = parse_filename(self.original_filename)

        # Save file to project storage
        await self._log_event(db, "INFO", "FILE_STORAGE_STARTED", "Saving file to project storage")
        saved_path = self.storage.save_uploaded_file(self.media_path, self.media_id, self.original_filename)
        await self._log_event(db, "INFO", "FILE_STORAGE_COMPLETED", f"Saved to: {saved_path}")

        # Build manifest
        await self._log_event(db, "INFO", "MANIFEST_BUILDING_STARTED", "Building media manifest")
        manifest = build_media_manifest(
            self.probe_data,
            self.media_id,
            self.original_filename,
            self.sha256,
            self.parser,
        )
        self.storage.save_manifest("media", manifest)
        await self._log_event(db, "INFO", "MANIFEST_BUILDING_COMPLETED", "Media manifest saved")

        # Create database records
        await self._create_database_records(db, manifest)

        # Update job status
        await self._complete_job(db, manifest)

    async def _create_database_records(self, db, manifest: dict) -> None:
        """Create database records for media.

        Args:
            db: Database manager.
            manifest: Media manifest.
        """
        async with db.session() as session:
            # Create episode
            episode = Episode(
                id=self.episode_id,
                project_id=self.project_id,
                season_number=self.filename_parse.season,
                episode_number=self.filename_parse.episode,
                title=self.filename_parse.title_candidate,
                duration_seconds=self.duration,
                status="INTAKE",
            )
            session.add(episode)

            # Create media asset
            media = MediaAsset(
                id=self.media_id,
                episode_id=self.episode_id,
                original_filename=self.original_filename,
                storage_path=str(self.storage.get_original_media_path(self.media_id)),
                file_size=self.file_size,
                sha256=self.sha256,
                duration_seconds=self.duration,
                container_format=manifest["container"]["format"],
                status="IMPORTED",
            )
            session.add(media)

            # Create subtitle assets for embedded subtitles
            for sub in manifest.get("subtitles", []):
                subtitle_asset = SubtitleAsset(
                    id=f"sub_{uuid.uuid4().hex[:12]}",
                    episode_id=self.episode_id,
                    media_id=self.media_id,
                    source_type="embedded",
                    language=sub.get("language"),
                    title=sub.get("title"),
                )
                session.add(subtitle_asset)

            # Create stream records
            # Video stream
            video = manifest.get("video")
            if video:
                video_stream = MediaStream(
                    media_id=self.media_id,
                    stream_index=video["index"],
                    stream_type="video",
                    codec=video.get("codec"),
                    width=video.get("width"),
                    height=video.get("height"),
                    fps=video.get("fps"),
                    is_default=video.get("is_default", False),
                    is_forced=False,
                )
                session.add(video_stream)

            # Audio streams
            for audio in manifest.get("audio", []):
                audio_stream = MediaStream(
                    media_id=self.media_id,
                    stream_index=audio["index"],
                    stream_type="audio",
                    codec=audio.get("codec"),
                    language=audio.get("language"),
                    title=audio.get("title"),
                    channels=audio.get("channels"),
                    channel_layout=audio.get("channel_layout"),
                    sample_rate=audio.get("sample_rate"),
                    bitrate=audio.get("bit_rate"),
                    is_default=audio.get("is_default", False),
                    is_forced=audio.get("is_forced", False),
                )
                session.add(audio_stream)

            # Subtitle streams
            for subtitle in manifest.get("subtitles", []):
                sub_stream = MediaStream(
                    media_id=self.media_id,
                    stream_index=subtitle["index"],
                    stream_type="subtitle",
                    codec=subtitle.get("codec"),
                    subtitle_codec=subtitle.get("codec"),  # For subtitle-specific codec
                    language=subtitle.get("language"),
                    title=subtitle.get("title"),
                    is_default=subtitle.get("is_default", False),
                    is_forced=subtitle.get("is_forced", False),
                )
                session.add(sub_stream)

            await session.commit()

    async def _complete_job(self, db, manifest: dict) -> None:
        """Mark job as completed.

        Args:
            db: Database manager.
            manifest: Media manifest.
        """
        async with db.session() as session:
            job = await session.get(Job, self.job_id)
            if job:
                job.status = "SUCCESS"
                job.finished_at = datetime.utcnow()
                job.output_manifest = str(manifest)

                event = JobEvent(
                    job_id=self.job_id,
                    level="INFO",
                    event_type="JOB_COMPLETED",
                    message=f"Media intake completed successfully",
                )
                session.add(event)

                await session.commit()

    async def _fail_job(self, db, error_message: str) -> None:
        """Mark job as failed.

        Args:
            db: Database manager.
            error_message: Error message.
        """
        async with db.session() as session:
            job = await session.get(Job, self.job_id)
            if job:
                job.status = "FAILED"
                job.finished_at = datetime.utcnow()
                job.error_message = error_message

                event = JobEvent(
                    job_id=self.job_id,
                    level="ERROR",
                    event_type="JOB_FAILED",
                    message=error_message,
                )
                session.add(event)

                await session.commit()

    async def _log_event(self, db, level: str, event_type: str, message: str) -> None:
        """Log a job event.

        Args:
            db: Database manager.
            level: Log level.
            event_type: Event type.
            message: Event message.
        """
        async with db.session() as session:
            event = JobEvent(
                job_id=self.job_id,
                level=level,
                event_type=event_type,
                message=message,
            )
            session.add(event)
            await session.commit()

    async def _update_project_status(self, db) -> None:
        """Update project status to READY_FOR_RESEARCH.

        Args:
            db: Database manager.
        """
        async with db.session() as session:
            project = await session.get(Project, self.project_id)
            if project:
                project.status = "READY_FOR_RESEARCH"
                await session.commit()
