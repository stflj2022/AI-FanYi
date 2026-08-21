"""Research manifest generation."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from filmdub.workers.research.models import (
    Actor,
    Appearance,
    Character,
    CharacterAlias,
    Episode,
    Project,
    Relationship,
    Source,
)


class ResearchManifestBuilder:
    """Build research manifest from database records."""

    SCHEMA_VERSION = "1.0"

    @staticmethod
    def build(
        project: Project,
        episode: Episode | None = None,
        characters: list[Character] | None = None,
        actors: list[Actor] | None = None,
        relationships: list[Relationship] | None = None,
        sources: list[Source] | None = None,
        evidence_count: int = 0,
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build research manifest.

        Args:
            project: Project record.
            episode: Episode record (optional).
            characters: List of character records.
            actors: List of actor records.
            relationships: List of relationship records.
            sources: List of source records.
            evidence_count: Number of evidence records.
            warnings: List of warning messages.

        Returns:
            dict: Research manifest.
        """
        manifest = {
            "schema_version": ResearchManifestBuilder.SCHEMA_VERSION,
            "project": {
                "id": project.id,
                "title": project.canonical_title,
                "original_title": project.original_title,
                "year": project.year,
                "tmdb_id": project.tmdb_id,
                "wikidata_id": project.wikidata_id,
                "imdb_id": project.imdb_id,
                "confidence": project.confidence,
            },
            "episode": None,
            "characters": [],
            "actors": [],
            "relationships": [],
            "evidence_count": evidence_count,
            "sources_count": len(sources) if sources else 0,
            "confidence": {
                "project": project.confidence,
            },
            "warnings": warnings or [],
            "generated_at": datetime.utcnow().isoformat(),
        }

        if episode:
            manifest["episode"] = {
                "id": episode.id,
                "season": episode.season,
                "episode": episode.episode,
                "title": episode.title,
                "original_title": episode.original_title,
                "air_date": episode.air_date,
                "runtime": episode.runtime,
                "tmdb_id": episode.tmdb_id,
                "wikidata_id": episode.wikidata_id,
                "confidence": episode.confidence,
            }
            manifest["confidence"]["episode"] = episode.confidence

        if characters:
            for char in characters:
                char_data = {
                    "id": char.id,
                    "canonical_name": char.canonical_name,
                    "original_name": char.original_name,
                    "actor_id": char.actor_id,
                    "character_type": char.character_type,
                    "description": char.description,
                    "confidence": char.confidence,
                    "aliases": [],
                }
                manifest["characters"].append(char_data)

        if actors:
            for actor in actors:
                actor_data = {
                    "id": actor.id,
                    "canonical_name": actor.canonical_name,
                    "original_name": actor.original_name,
                    "tmdb_id": actor.tmdb_id,
                    "wikidata_id": actor.wikidata_id,
                    "imdb_id": actor.imdb_id,
                    "gender": actor.gender,
                    "birth_date": actor.birth_date,
                    "confidence": actor.confidence,
                }
                manifest["actors"].append(actor_data)

        if relationships:
            for rel in relationships:
                rel_data = {
                    "id": rel.id,
                    "subject_id": rel.subject_id,
                    "relation": rel.relation,
                    "object_id": rel.object_id,
                    "confidence": rel.confidence,
                    "valid_from_episode_id": rel.valid_from_episode_id,
                    "valid_to_episode_id": rel.valid_to_episode_id,
                }
                manifest["relationships"].append(rel_data)

        return manifest

    @staticmethod
    def save(manifest: dict, output_path: Path) -> None:
        """Save manifest to file.

        Args:
            manifest: Manifest data.
            output_path: Output file path.
        """
        # Atomic write
        temp_path = output_path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        temp_path.replace(output_path)
