"""Test Module 02 - Research Worker."""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from workers.research.config import ResearchConfig, get_research_config
from workers.research.identity import IdentityResolver
from workers.research.init_db import init_research_database
from workers.research.manifest import ResearchManifestBuilder
from workers.research.runner import ResearchWorker


class TestResearchConfig:
    """Test research configuration."""

    def test_get_config(self):
        """Test getting research configuration."""
        config = get_research_config()
        assert isinstance(config, ResearchConfig)
        assert config.confidence_threshold_merge == 0.90
        assert config.confidence_threshold_review == 0.70
        assert config.reliability_tmdb == 95.0

    def test_config_defaults(self):
        """Test configuration defaults."""
        config = ResearchConfig()
        assert config.tmdb_api_key is None
        assert config.cache_enabled is True
        assert config.confidence_threshold_merge == 0.90
        assert config.reliability_tmdb == 95.0


class TestIdentityResolver:
    """Test identity resolution."""

    def test_parse_filename_with_season_episode(self):
        """Test parsing filename with season/episode."""
        resolver = IdentityResolver()
        result = resolver.parse_filename("Breaking.Bad.S01E01.1080p.WEB-DL.mkv")

        assert result["title"] == "Breaking Bad"
        assert result["season"] == 1
        assert result["episode"] == 1
        assert result["confidence"] == 0.8

    def test_parse_filename_with_x_format(self):
        """Test parsing filename with 1x01 format."""
        resolver = IdentityResolver()
        result = resolver.parse_filename("Game of Thrones 1x01.mkv")

        assert result["season"] == 1
        assert result["episode"] == 1

    def test_parse_filename_chinese(self):
        """Test parsing Chinese filename."""
        resolver = IdentityResolver()
        result = resolver.parse_filename("绝命毒师第1季第1集.mkv")

        assert result["season"] == 1
        assert result["episode"] == 1

    def test_clean_title(self):
        """Test title cleaning."""
        resolver = IdentityResolver()
        title = resolver._clean_title("Breaking.Bad.S01E01.1080p.WEB-DL.x265")
        assert title == "Breaking Bad"

    def test_resolve_identity(self):
        """Test full identity resolution."""
        resolver = IdentityResolver()
        identity = resolver.resolve_identity(
            filename="Breaking.Bad.S01E01.mkv",
            project_title="Breaking Bad",
            duration=3480.0,
        )

        assert identity["title"] == "Breaking Bad"
        assert identity["season"] == 1
        assert identity["episode"] == 1
        assert identity["confidence"] > 0


class TestManifestBuilder:
    """Test manifest builder."""

    def test_build_basic_manifest(self):
        """Test building basic manifest."""
        from workers.research.models import Project

        project = Project(
            id="test_project",
            canonical_title="Test Show",
            original_title="Test Show",
            year=2020,
            media_type="tv",
            tmdb_id=12345,
            confidence=0.95,
        )

        manifest = ResearchManifestBuilder.build(project=project)

        assert manifest["schema_version"] == "1.0"
        assert manifest["project"]["id"] == "test_project"
        assert manifest["project"]["title"] == "Test Show"
        assert manifest["project"]["year"] == 2020
        assert manifest["project"]["confidence"] == 0.95


class TestResearchWorker:
    """Test research worker."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create temporary project directory."""
        project_dir = tmp_path / "proj_test123"
        project_dir.mkdir()
        (project_dir / "research").mkdir()
        (project_dir / "manifests").mkdir()
        return project_dir

    @pytest.fixture
    def media_manifest(self, temp_project_dir):
        """Create media manifest."""
        manifest = {
            "container": {
                "duration": 3480.0,
                "format": "matroska,webm",
            },
            "file": {
                "name": "Breaking.Bad.S01E01.1080p.WEB-DL.mkv",
                "size": 2500000000,
            },
            "video": {
                "codec": "h264",
                "width": 1920,
                "height": 1080,
            },
            "audio": [
                {
                    "id": "audio_0",
                    "codec": "dts",
                    "language": "eng",
                }
            ],
            "subtitles": [
                {
                    "id": "sub_0",
                    "language": "eng",
                }
            ],
            "hints": {
                "title": "Breaking Bad",
                "season": 1,
                "episode": 1,
            },
        }

        manifest_path = temp_project_dir / "manifests" / "media.json"
        with manifest_path.open("w") as f:
            json.dump(manifest, f)

        # Create project manifest
        project_manifest = {
            "schema_version": "1.0",
            "project": {
                "id": "proj_test123",
                "title": "Breaking Bad",
                "status": "READY_FOR_RESEARCH",
            },
        }

        project_manifest_path = temp_project_dir / "manifests" / "project.json"
        with project_manifest_path.open("w") as f:
            json.dump(project_manifest, f)

        return manifest_path

    @pytest.mark.asyncio
    async def test_worker_creation(self, temp_project_dir, media_manifest):
        """Test creating research worker."""
        worker = ResearchWorker(
            project_id="proj_test123",
            media_manifest_path=media_manifest,
            project_title="Breaking Bad",
            duration=3480.0,
        )

        assert worker.project_id == "proj_test123"
        assert worker.project_title == "Breaking Bad"
        assert worker.duration == 3480.0
        assert worker.research_dir.exists()

    @pytest.mark.asyncio
    async def test_worker_load_media_manifest(self, temp_project_dir, media_manifest):
        """Test loading media manifest."""
        worker = ResearchWorker(
            project_id="proj_test123",
            media_manifest_path=media_manifest,
            project_title="Breaking Bad",
        )

        await worker._load_media_manifest()

        assert worker.media_manifest is not None
        assert worker.media_manifest["file"]["name"] == "Breaking.Bad.S01E01.1080p.WEB-DL.mkv"
        assert worker.media_manifest["container"]["duration"] == 3480.0


if __name__ == "__main__":
    # Run basic tests
    print("Running Module 02 Tests...")

    # Test Identity Resolver
    print("\n[1] Testing Identity Resolver...")
    resolver = IdentityResolver()

    result = resolver.parse_filename("Breaking.Bad.S01E01.1080p.WEB-DL.mkv")
    print(f"  ✓ Parsed: {result['title']} S{result['season']:02d}E{result['episode']:02d}")

    result = resolver.parse_filename("Game of Thrones 1x01.mkv")
    print(f"  ✓ Parsed: {result['season']}x{result['episode']:02d}")

    result = resolver.parse_filename("绝命毒师第1季第1集.mkv")
    print(f"  ✓ Parsed Chinese: S{result['season']:02d}E{result['episode']:02d}")

    # Test Config
    print("\n[2] Testing Config...")
    config = get_research_config()
    print(f"  ✓ Config loaded: merge_threshold={config.confidence_threshold_merge}")
    print(f"  ✓ TMDB reliability: {config.reliability_tmdb}")

    # Test Manifest Builder
    print("\n[3] Testing Manifest Builder...")
    from workers.research.models import Project
    project = Project(
        id="test_proj",
        canonical_title="Test Show",
        year=2020,
        confidence=0.95,
    )
    manifest = ResearchManifestBuilder.build(project=project)
    print(f"  ✓ Manifest built: {manifest['project']['title']}")

    print("\n✓ All basic tests passed!")
