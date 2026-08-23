"""Research worker - coordinates all research steps."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select

from filmdub.core.config import settings
from filmdub.core.orchestrator_db import get_database_manager
from filmdub.workers.research.config import get_research_config
from filmdub.workers.research.identity import IdentityResolver
from filmdub.workers.research.init_db import init_research_database
from filmdub.workers.research.manifest import ResearchManifestBuilder
from filmdub.workers.research.models import (
    Actor,
    Appearance,
    Character,
    CharacterAlias,
    Episode,
    Project,
    Relationship,
    ResearchJob,
    Source,
    Evidence,
)
from filmdub.workers.research.sources.tmdb import get_tmdb_adapter
from filmdub.workers.research.sources.wikidata import get_wikidata_adapter
from filmdub.workers.research.sources.web_search import get_web_search_adapter
from filmdub.workers.research.extract import get_qwen_extractor
from filmdub.workers.research.resolve import get_entity_resolver
from filmdub.workers.research.verify import get_research_verifier

logger = logging.getLogger(__name__)


class ResearchWorker:
    """Main research worker that coordinates all research steps."""

    def __init__(
        self,
        project_id: str,
        media_manifest_path: Path,
        project_title: str,
        duration: Optional[float] = None,
    ):
        """Initialize research worker.

        Args:
            project_id: Project ID.
            media_manifest_path: Path to media manifest.
            project_title: Project title.
            duration: Media duration in seconds.
        """
        self.project_id = project_id
        self.media_manifest_path = media_manifest_path
        self.project_title = project_title
        self.duration = duration
        self.config = get_research_config()
        self.identity_resolver = IdentityResolver()
        self.tmdb_adapter = get_tmdb_adapter()
        self.wikidata_adapter = get_wikidata_adapter()
        self.web_search_adapter = get_web_search_adapter(project_id)
        self.qwen_extractor = get_qwen_extractor(project_id)
        self.entity_resolver = get_entity_resolver()
        self.verifier = get_research_verifier()

        # Storage paths
        self.projects_dir = settings.projects_base_dir
        self.project_dir = self.projects_dir / project_id
        self.research_dir = self.project_dir / "research"
        self.research_dir.mkdir(parents=True, exist_ok=True)

        # Subdirectories
        (self.research_dir / "cache").mkdir(exist_ok=True)
        (self.research_dir / "raw").mkdir(exist_ok=True)
        (self.research_dir / "evidence").mkdir(exist_ok=True)
        (self.research_dir / "entities").mkdir(exist_ok=True)

        # State
        self.warnings: list[str] = []
        self.media_manifest: dict = {}

        # Database
        self.db = get_database_manager(project_id)

    async def run(self) -> dict[str, Any]:
        """Run full research pipeline.

        Returns:
            dict: Research result.
        """
        # Initialize database
        await init_research_database(self.project_id)

        # Load media manifest
        await self._load_media_manifest()

        # Step 1: Identity Resolution
        await self._step_identity()

        # Step 2: TMDB Research
        await self._step_tmdb()

        # Step 3: Episode Identification
        await self._step_episode()

        # Step 4: Cast Extraction
        await self._step_cast()

        # Step 5: Character Extraction
        await self._step_characters()

        # Step 6: Wikidata Research
        await self._step_wikidata()

        # Step 7: Web Search
        await self._step_web_search()

        # Step 8: Qwen Extraction
        await self._step_qwen_extraction()

        # Step 9: Entity Resolution
        await self._step_entity_resolution()

        # Step 10: Relationship Extraction
        await self._step_relationships()

        # Step 11: Verification
        await self._step_verification()

        # Step 12: Build Manifest
        manifest_path = await self._step_manifest()

        # Update project status
        await self._update_project_status("READY_FOR_CHARACTERS")

        return {
            "job_id": f"job_{uuid.uuid4().hex[:12]}",
            "manifest_path": str(manifest_path),
            "status": "SUCCESS",
            "warnings": self.warnings,
        }

    async def _load_media_manifest(self) -> None:
        """Load media manifest file."""
        if not self.media_manifest_path.exists():
            raise FileNotFoundError(f"Media manifest not found: {self.media_manifest_path}")

        with self.media_manifest_path.open("r") as f:
            self.media_manifest = json.load(f)

        logger.info(f"Loaded media manifest: {self.media_manifest_path}")

    async def _create_job(self, step: str) -> ResearchJob:
        """Create a research job record.

        Args:
            step: Step name.

        Returns:
            ResearchJob: Created job record.
        """
        job = ResearchJob(
            id=f"job_{uuid.uuid4().hex[:12]}",
            project_id=self.project_id,
            step=step,
            status="RUNNING",
            started_at=datetime.utcnow(),
        )

        await self.db.initialize()
        async with self.db.session() as session:
            session.add(job)
            await session.commit()
            await session.refresh(job)

        logger.info(f"Created job: {job.id} - {step}")
        return job

    async def _update_job(
        self,
        job: ResearchJob,
        status: str,
        error_message: Optional[str] = None,
        output_data: Optional[dict] = None,
    ) -> None:
        """Update job status.

        Args:
            job: Job to update.
            status: New status.
            error_message: Error message if failed.
            output_data: Output data.
        """
        job.status = status
        job.finished_at = datetime.utcnow()
        job.error_message = error_message
        if output_data:
            job.output_data = json.dumps(output_data)

        await self.db.initialize()
        async with self.db.session() as session:
            await session.merge(job)
            await session.commit()

        logger.info(f"Updated job {job.id}: {status}")

    async def _step_identity(self) -> None:
        """Step 1: Identity Resolution."""
        job = await self._create_job("identity")

        try:
            logger.info("Step 1: Identity Resolution")

            # Get filename from media manifest
            # Support both formats: media.json and media_manifest.json
            filename = None
            if "file" in self.media_manifest:
                filename = self.media_manifest.get("file", {}).get("name")
            elif "filename" in self.media_manifest:
                filename = self.media_manifest.get("filename")

            # Resolve identity
            identity = self.identity_resolver.resolve_identity(
                filename=filename,
                project_title=self.project_title,
                duration=self.duration,
            )

            logger.info(f"Resolved identity: {identity}")

            # Save raw identity data
            raw_file = self.research_dir / "raw" / "01_identity.json"
            with raw_file.open("w") as f:
                json.dump(identity, f, indent=2)

            # Update job
            await self._update_job(job, "SUCCESS", output_data=identity)

        except Exception as e:
            logger.error(f"Identity resolution failed: {e}")
            await self._update_job(job, "FAILED", error_message=str(e))
            raise

    async def _step_tmdb(self) -> None:
        """Step 2: TMDB Research."""
        job = await self._create_job("tmdb")

        try:
            logger.info("Step 2: TMDB Research")

            # Load identity from previous step
            raw_file = self.research_dir / "raw" / "01_identity.json"
            with raw_file.open("r") as f:
                identity = json.load(f)

            title = identity.get("title")
            if not title:
                raise ValueError("No title found from identity resolution")

            # Search TMDB
            search_results = await self.tmdb_adapter.search_tv_show(title)
            if not search_results:
                self.warnings.append("TMDB search returned no results")
                await self._update_job(job, "SUCCESS_WITH_WARNINGS")
                return

            # Get first result
            results = search_results.get("results", [])
            if not results:
                self.warnings.append("No TMDB results found")
                await self._update_job(job, "SUCCESS_WITH_WARNINGS")
                return

            show = results[0]
            tmdb_id = show.get("id")
            show_title = show.get("name")
            show_overview = show.get("overview")
            first_air_date = show.get("first_air_date")
            year = int(first_air_date.split("-")[0]) if first_air_date else None

            logger.info(f"Found TMDB show: {show_title} (ID: {tmdb_id})")

            # Get full show details
            show_details = await self.tmdb_adapter.get_tv_details(tmdb_id)

            # Get season details
            season = identity.get("season", 1)
            season_details = await self.tmdb_adapter.get_season_details(tmdb_id, season)

            # Get episode details
            episode = identity.get("episode", 1)
            if season_details:
                episode_details = await self.tmdb_adapter.get_episode_details(tmdb_id, season, episode)
            else:
                episode_details = None

            # Get credits
            credits = await self.tmdb_adapter.get_tv_credits(tmdb_id)

            # Compile TMDB data
            tmdb_data = {
                "show": show_details,
                "season": season_details,
                "episode": episode_details,
                "credits": credits,
                "search_results": search_results,
            }

            # Save raw data
            raw_file = self.research_dir / "raw" / "02_tmdb.json"
            with raw_file.open("w") as f:
                json.dump(tmdb_data, f, indent=2, default=str)

            # Save to database
            await self._save_tmdb_to_db(tmdb_data, show, show_details, episode_details, credits)

            await self._update_job(job, "SUCCESS", output_data=tmdb_data)

        except Exception as e:
            logger.error(f"TMDB research failed: {e}")
            self.warnings.append(f"TMDB research failed: {e}")
            await self._update_job(job, "FAILED", error_message=str(e))
            raise

    async def _save_tmdb_to_db(
        self,
        tmdb_data: dict,
        show: dict,
        show_details: dict,
        episode_details: Optional[dict],
        credits: Optional[dict],
    ) -> None:
        """Save TMDB data to database.

        Args:
            tmdb_data: Full TMDB data.
            show: Show search result.
            show_details: Show details.
            episode_details: Episode details.
            credits: Credits data.
        """
        await self.db.initialize()
        async with self.db.session() as session:
            # Create project record
            project = Project(
                id=self.project_id,
                canonical_title=show.get("name", self.project_title),
                original_title=show.get("original_name"),
                year=int(show.get("first_air_date", "2000")[:4]) if show.get("first_air_date") else None,
                media_type="tv",
                tmdb_id=show.get("id"),
                confidence=0.95,
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)

            # Create episode record
            if episode_details:
                episode = Episode(
                    id=f"ep_{self.project_id}_s{episode_details.get('season_number', 1):02d}e{episode_details.get('episode_number', 1):02d}",
                    project_id=self.project_id,
                    season=episode_details.get("season_number", 1),
                    episode=episode_details.get("episode_number", 1),
                    title=episode_details.get("name"),
                    overview=episode_details.get("overview"),
                    air_date=episode_details.get("air_date"),
                    runtime=episode_details.get("runtime"),
                    tmdb_id=episode_details.get("id"),
                    confidence=0.95,
                )
                session.add(episode)
                await session.commit()
                await session.refresh(episode)
                self.current_episode = episode

            # Create source record
            source = Source(
                id=f"src_tmdb_{show.get('id')}",
                project_id=self.project_id,
                source_type="tmdb",
                url=f"https://www.themoviedb.org/tv/{show.get('id')}",
                title=f"TMDB: {show.get('name')}",
                reliability=self.config.reliability_tmdb / 100.0,
                status="success",
            )
            session.add(source)
            await session.commit()
            await session.refresh(source)
            self.tmdb_source_id = source.id

            # Create actor records
            if credits:
                cast = credits.get("cast", [])[:20]  # Top 20 actors
                for i, cast_member in enumerate(cast):
                    actor_id = f"actor_tmdb_{cast_member.get('id', i)}"
                    actor = Actor(
                        id=actor_id,
                        project_id=self.project_id,
                        canonical_name=cast_member.get("name"),
                        original_name=cast_member.get("original_name"),
                        tmdb_id=cast_member.get("id"),
                        gender=cast_member.get("gender"),
                        profile_path=cast_member.get("profile_path"),
                        confidence=0.95,
                    )
                    session.add(actor)

                    # Add evidence
                    evidence = Evidence(
                        id=f"ev_actor_{actor_id}",
                        project_id=self.project_id,
                        entity_type="actor",
                        entity_id=actor_id,
                        predicate="name",
                        value=cast_member.get("name"),
                        source_id=source.id,
                        confidence=0.95,
                    )
                    session.add(evidence)

                await session.commit()
                self.tmdb_cast = cast

            logger.info(f"Saved TMDB data to database for project {self.project_id}")

    async def _step_episode(self) -> None:
        """Step 3: Episode Identification."""
        job = await self._create_job("episode")

        try:
            logger.info("Step 3: Episode Identification")

            # Episode is already identified in TMDB step
            if hasattr(self, "current_episode"):
                logger.info(f"Episode identified: S{self.current_episode.season}E{self.current_episode.episode}")
                await self._update_job(job, "SUCCESS", output_data={
                    "season": self.current_episode.season,
                    "episode": self.current_episode.episode,
                    "title": self.current_episode.title,
                })
            else:
                self.warnings.append("Episode not identified in TMDB step")
                await self._update_job(job, "SKIPPED")

        except Exception as e:
            logger.error(f"Episode identification failed: {e}")
            await self._update_job(job, "FAILED", error_message=str(e))
            raise

    async def _step_cast(self) -> None:
        """Step 4: Cast Extraction."""
        job = await self._create_job("cast")

        try:
            logger.info("Step 4: Cast Extraction")

            # Cast is already extracted in TMDB step
            if hasattr(self, "tmdb_cast"):
                logger.info(f"Cast extracted: {len(self.tmdb_cast)} actors")
                await self._update_job(job, "SUCCESS", output_data={
                    "count": len(self.tmdb_cast),
                })
            else:
                self.warnings.append("Cast not extracted in TMDB step")
                await self._update_job(job, "SKIPPED")

        except Exception as e:
            logger.error(f"Cast extraction failed: {e}")
            await self._update_job(job, "FAILED", error_message=str(e))
            raise

    async def _step_characters(self) -> None:
        """Step 5: Character Extraction."""
        job = await self._create_job("characters")

        try:
            logger.info("Step 5: Character Extraction")

            # Extract characters from cast
            if not hasattr(self, "tmdb_cast"):
                self.warnings.append("No cast data available for character extraction")
                await self._update_job(job, "SKIPPED")
                return

            await self.db.initialize()
            async with self.db.session() as session:
                # Get actors
                stmt = select(Actor).where(Actor.project_id == self.project_id)
                result = await session.execute(stmt)
                actors = result.scalars().all()

                # Create characters from cast
                for i, cast_member in enumerate(self.tmdb_cast):
                    character_name = cast_member.get("character", "Unknown")
                    if not character_name or character_name.lower() in ["self", "himself", "herself"]:
                        continue

                    # Find or create actor
                    actor = next((a for a in actors if a.tmdb_id == cast_member.get("id")), None)

                    character_id = f"char_{self.project_id}_{i:03d}"
                    character = Character(
                        id=character_id,
                        project_id=self.project_id,
                        canonical_name=character_name,
                        actor_id=actor.id if actor else None,
                        character_type="main" if i < 5 else "recurring",
                        description=cast_member.get("character"),
                        confidence=0.90,
                    )
                    session.add(character)

                    # Create appearance if episode exists
                    if hasattr(self, "current_episode"):
                        appearance = Appearance(
                            character_id=character_id,
                            episode_id=self.current_episode.id,
                            appearance_type="main" if i < 5 else "recurring",
                            confidence=0.85,
                        )
                        session.add(appearance)

                    # Add evidence
                    if hasattr(self, "tmdb_source_id"):
                        evidence = Evidence(
                            id=f"ev_char_{character_id}",
                            project_id=self.project_id,
                            entity_type="character",
                            entity_id=character_id,
                            predicate="portrayed_by",
                            value=f"actor:{actor.id}" if actor else "",
                            source_id=self.tmdb_source_id,
                            confidence=0.90,
                        )
                        session.add(evidence)

                await session.commit()

            logger.info("Character extraction completed")
            await self._update_job(job, "SUCCESS")

        except Exception as e:
            logger.error(f"Character extraction failed: {e}")
            await self._update_job(job, "FAILED", error_message=str(e))
            raise

    async def _step_manifest(self) -> Path:
        """Step 6: Build Research Manifest."""
        job = await self._create_job("manifest")

        try:
            logger.info("Step 6: Build Research Manifest")

            await self.db.initialize()
            async with self.db.session() as session:
                # Get project
                project = await session.get(Project, self.project_id)

                # Get episode
                stmt = select(Episode).where(Episode.project_id == self.project_id)
                result = await session.execute(stmt)
                episode = result.scalar_one_or_none()

                # Get characters
                stmt = select(Character).where(Character.project_id == self.project_id)
                result = await session.execute(stmt)
                characters = result.scalars().all()

                # Get actors
                stmt = select(Actor).where(Actor.project_id == self.project_id)
                result = await session.execute(stmt)
                actors = result.scalars().all()

                # Get sources
                stmt = select(Source).where(Source.project_id == self.project_id)
                result = await session.execute(stmt)
                sources = result.scalars().all()

                # Get evidence count
                stmt = select(Evidence).where(Evidence.project_id == self.project_id)
                result = await session.execute(stmt)
                evidence_count = len(result.scalars().all())

                # Build manifest
                manifest = ResearchManifestBuilder.build(
                    project=project,
                    episode=episode,
                    characters=list(characters),
                    actors=list(actors),
                    sources=list(sources),
                    evidence_count=evidence_count,
                    warnings=self.warnings,
                )

                # Save manifest
                manifest_path = self.project_dir / "research_manifest.json"
                ResearchManifestBuilder.save(manifest, manifest_path)

                logger.info(f"Research manifest saved: {manifest_path}")
                await self._update_job(job, "SUCCESS", output_data={"path": str(manifest_path)})

                return manifest_path

        except Exception as e:
            logger.error(f"Manifest build failed: {e}")
            await self._update_job(job, "FAILED", error_message=str(e))
            raise

    async def _update_project_status(self, status: str) -> None:
        """Update project status in database.

        Args:
            status: New status.
        """
        from filmdub.core.models import Project as CoreProject

        await self.db.initialize()
        async with self.db.session() as session:
            project = await session.get(CoreProject, self.project_id)
            if project:
                project.status = status
                project.updated_at = datetime.utcnow()
                await session.commit()

                # Update manifest
                from filmdub.core.storage import StorageManager
                storage = StorageManager(self.project_id)
                project_manifest = storage.load_manifest("project")
                if project_manifest:
                    project_manifest["project"]["status"] = status
                    project_manifest["project"]["updated_at"] = datetime.utcnow().isoformat()
                    storage.save_manifest("project", project_manifest)

                logger.info(f"Project status updated: {status}")

    async def _step_wikidata(self) -> None:
        """Step 6: Wikidata Research."""
        job = await self._create_job("wikidata")

        try:
            logger.info("Step 6: Wikidata Research")

            # Load identity
            raw_file = self.research_dir / "raw" / "01_identity.json"
            with raw_file.open("r") as f:
                identity = json.load(f)

            title = identity.get("title")
            if not title:
                await self._update_job(job, "SKIPPED")
                return

            # Get work info from Wikidata
            work_info = await self.wikidata_adapter.get_work_info(title)

            wikidata_data = {
                "work": work_info,
            }

            # Save raw data
            raw_file = self.research_dir / "raw" / "03_wikidata.json"
            with raw_file.open("w") as f:
                json.dump(wikidata_data, f, indent=2, default=str)

            # Update database with Wikidata IDs
            if work_info:
                await self.db.initialize()
                async with self.db.session() as session:
                    project = await session.get(Project, self.project_id)
                    if project:
                        project.wikidata_id = work_info.get("wikidata_id")
                        await session.commit()

                        # Create source record
                        source = Source(
                            id=f"src_wikidata_{work_info.get('wikidata_id', 'unknown')}",
                            project_id=self.project_id,
                            source_type="wikidata",
                            url=f"https://www.wikidata.org/wiki/{work_info.get('wikidata_id', '')}",
                            title=f"Wikidata: {work_info.get('title', title)}",
                            reliability=self.config.reliability_wikidata / 100.0,
                            status="success",
                        )
                        session.add(source)
                        await session.commit()
                        self.wikidata_source_id = source.id

            await self._update_job(job, "SUCCESS", output_data=wikidata_data)

        except Exception as e:
            logger.error(f"Wikidata research failed: {e}")
            self.warnings.append(f"Wikidata research failed: {e}")
            await self._update_job(job, "SUCCESS_WITH_WARNINGS")

    async def _step_web_search(self) -> None:
        """Step 7: Web Search Research."""
        job = await self._create_job("web_search")

        try:
            logger.info("Step 7: Web Search Research")

            # Load identity
            raw_file = self.research_dir / "raw" / "01_identity.json"
            with raw_file.open("r") as f:
                identity = json.load(f)

            title = identity.get("title")
            season = identity.get("season")
            episode = identity.get("episode")

            if not title:
                await self._update_job(job, "SKIPPED")
                return

            # Search for work
            work_results = await self.web_search_adapter.search_work(title, season, episode)

            web_search_data = {
                "work_results": work_results,
            }

            # Save raw data
            raw_file = self.research_dir / "raw" / "04_web_search.json"
            with raw_file.open("w") as f:
                json.dump(web_search_data, f, indent=2)

            # Collect documents for Qwen
            self.web_documents = []
            for result in work_results:
                doc = await self.web_search_adapter.fetch_url(result.get("url", ""))
                if doc:
                    self.web_documents.append({
                        "url": doc.get("url"),
                        "title": result.get("title"),
                        "text": doc.get("text", ""),
                        "source_id": result.get("source_id"),
                    })

            await self._update_job(job, "SUCCESS", output_data={"document_count": len(self.web_documents)})

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            self.warnings.append(f"Web search failed: {e}")
            await self._update_job(job, "SUCCESS_WITH_WARNINGS")

    async def _step_qwen_extraction(self) -> None:
        """Step 8: Qwen LLM Extraction."""
        job = await self._create_job("qwen_extraction")

        try:
            logger.info("Step 8: Qwen LLM Extraction")

            # Check if we have documents
            if not hasattr(self, "web_documents") or len(self.web_documents) == 0:
                logger.info("No web documents for Qwen extraction")
                await self._update_job(job, "SKIPPED")
                return

            # Load identity
            raw_file = self.research_dir / "raw" / "01_identity.json"
            with raw_file.open("r") as f:
                identity = json.load(f)

            title = identity.get("title")

            # Extract characters
            extraction_result = await self.qwen_extractor.extract_characters(
                work_title=title,
                documents=self.web_documents,
            )

            # Save extraction result
            raw_file = self.research_dir / "raw" / "05_qwen_extraction.json"
            with raw_file.open("w") as f:
                json.dump(extraction_result, f, indent=2)

            self.qwen_characters = extraction_result.get("characters", [])
            self.qwen_relationships = extraction_result.get("relationships", [])

            logger.info(f"Qwen extracted {len(self.qwen_characters)} characters, {len(self.qwen_relationships)} relationships")
            await self._update_job(job, "SUCCESS", output_data=extraction_result)

        except Exception as e:
            logger.error(f"Qwen extraction failed: {e}")
            self.warnings.append(f"Qwen extraction failed: {e}")
            await self._update_job(job, "SUCCESS_WITH_WARNINGS")

    async def _step_entity_resolution(self) -> None:
        """Step 9: Entity Resolution."""
        job = await self._create_job("entity_resolution")

        try:
            logger.info("Step 9: Entity Resolution")

            await self.db.initialize()
            async with self.db.session() as session:
                # Get existing characters
                stmt = select(Character).where(Character.project_id == self.project_id)
                result = await session.execute(stmt)
                existing_chars = [
                    {
                        "id": c.id,
                        "canonical_name": c.canonical_name,
                        "actor_id": c.actor_id,
                        "description": c.description,
                        "confidence": c.confidence,
                    }
                    for c in result.scalars().all()
                ]

            # Combine with Qwen characters
            all_characters = existing_chars + [
                {
                    "id": f"qwen_char_{i}",
                    "canonical_name": c.get("name"),
                    "description": c.get("description"),
                    "confidence": 0.8,
                }
                for i, c in enumerate(self.qwen_characters)
                if hasattr(self, "qwen_characters")
            ]

            # Resolve duplicates
            resolved, merged_pairs = self.entity_resolver.resolve_characters(all_characters)

            # Create ID mapping
            id_map: dict[str, str] = {}
            for pair in merged_pairs:
                old_id, new_id, _ = pair
                id_map[old_id] = new_id

            # Update database with resolved characters
            await self._save_resolved_characters(resolved)

            resolution_data = {
                "resolved_count": len(resolved),
                "merged_pairs": merged_pairs,
            }

            # Save resolution result
            raw_file = self.research_dir / "raw" / "06_entity_resolution.json"
            with raw_file.open("w") as f:
                json.dump(resolution_data, f, indent=2)

            self.character_id_map = id_map
            logger.info(f"Resolved {len(all_characters)} characters to {len(resolved)} unique entities")
            await self._update_job(job, "SUCCESS", output_data=resolution_data)

        except Exception as e:
            logger.error(f"Entity resolution failed: {e}")
            self.warnings.append(f"Entity resolution failed: {e}")
            await self._update_job(job, "SUCCESS_WITH_WARNINGS")

    async def _save_resolved_characters(self, characters: list[dict]) -> None:
        """Save resolved characters to database.

        Args:
            characters: List of resolved characters.
        """
        await self.db.initialize()
        async with self.db.session() as session:
            # Get existing characters
            stmt = select(Character).where(Character.project_id == self.project_id)
            result = await session.execute(stmt)
            existing = {c.id: c for c in result.scalars().all()}

            for char in characters:
                char_id = char.get("id")

                if char_id in existing:
                    # Update existing
                    existing[char_id].canonical_name = char.get("canonical_name")
                    existing[char_id].confidence = char.get("confidence", 0.8)
                else:
                    # Create new
                    character = Character(
                        id=char_id,
                        project_id=self.project_id,
                        canonical_name=char.get("canonical_name"),
                        actor_id=char.get("actor_id"),
                        description=char.get("description"),
                        confidence=char.get("confidence", 0.8),
                    )
                    session.add(character)

            await session.commit()

    async def _step_relationships(self) -> None:
        """Step 10: Relationship Extraction."""
        job = await self._create_job("relationships")

        try:
            logger.info("Step 10: Relationship Extraction")

            # Combine Qwen relationships with any manual additions
            all_relationships = self.qwen_relationships if hasattr(self, "qwen_relationships") else []

            # Normalize and resolve relationships
            id_map = self.character_id_map if hasattr(self, "character_id_map") else {}
            resolved_relationships = self.entity_resolver.resolve_relationships(
                all_relationships,
                id_map,
            )

            # Save to database
            await self.db.initialize()
            async with self.db.session() as session:
                for rel in resolved_relationships:
                    relationship = Relationship(
                        id=f"rel_{uuid.uuid4().hex[:12]}",
                        project_id=self.project_id,
                        subject_id=rel.get("subject"),
                        relation=rel.get("relation"),
                        object_id=rel.get("object"),
                        confidence=rel.get("confidence", 0.8),
                    )
                    session.add(relationship)

                await session.commit()

            # Save relationships result
            raw_file = self.research_dir / "raw" / "07_relationships.json"
            with raw_file.open("w") as f:
                json.dump({"relationships": resolved_relationships}, f, indent=2)

            logger.info(f"Saved {len(resolved_relationships)} relationships")
            await self._update_job(job, "SUCCESS", output_data={"count": len(resolved_relationships)})

        except Exception as e:
            logger.error(f"Relationship extraction failed: {e}")
            self.warnings.append(f"Relationship extraction failed: {e}")
            await self._update_job(job, "SUCCESS_WITH_WARNINGS")

    async def _step_verification(self) -> None:
        """Step 11: Verification."""
        job = await self._create_job("verification")

        try:
            logger.info("Step 11: Verification")

            # Build manifest for verification
            await self.db.initialize()
            async with self.db.session() as session:
                # Get project
                project = await session.get(Project, self.project_id)

                # Get episode
                stmt = select(Episode).where(Episode.project_id == self.project_id)
                result = await session.execute(stmt)
                episode = result.scalar_one_or_none()

                # Get characters
                stmt = select(Character).where(Character.project_id == self.project_id)
                result = await session.execute(stmt)
                characters = [c.__dict__ for c in result.scalars().all()]

                # Get actors
                stmt = select(Actor).where(Actor.project_id == self.project_id)
                result = await session.execute(stmt)
                actors = [a.__dict__ for a in result.scalars().all()]

                # Get sources
                stmt = select(Source).where(Source.project_id == self.project_id)
                result = await session.execute(stmt)
                sources = [s.__dict__ for s in result.scalars().all()]

                # Get relationships
                stmt = select(Relationship).where(Relationship.project_id == self.project_id)
                result = await session.execute(stmt)
                relationships = [r.__dict__ for r in result.scalars().all()]

                # Build temporary manifest
                manifest = ResearchManifestBuilder.build(
                    project=project,
                    episode=episode,
                    characters=characters,
                    actors=actors,
                    sources=sources,
                    relationships=relationships,
                    evidence_count=0,
                    warnings=self.warnings,
                )

            # Verify manifest
            verification_result = self.verifier.verify_manifest(manifest)

            # Save verification result
            raw_file = self.research_dir / "raw" / "08_verification.json"
            with raw_file.open("w") as f:
                json.dump(verification_result, f, indent=2)

            # Add verification warnings/errors to warnings list
            if verification_result.get("warnings"):
                self.warnings.extend(verification_result["warnings"])

            if verification_result.get("errors"):
                self.warnings.extend(verification_result["errors"])

            logger.info(f"Verification: {verification_result.get('status')}")
            await self._update_job(
                job,
                verification_result.get("status", "SUCCESS"),
                output_data=verification_result,
            )

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            self.warnings.append(f"Verification failed: {e}")
            await self._update_job(job, "SUCCESS_WITH_WARNINGS")
