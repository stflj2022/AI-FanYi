"""Tests for Media Intake Worker."""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

try:
    from filmdub.core.config import settings
    from filmdub.core.orchestrator_db import get_database_manager
    from filmdub.core.models import Base, Job, MediaAsset, Project
    from filmdub.workers.media_intake.filename_parser import parse_filename
    from filmdub.workers.media_intake.hashing import compute_sha256
    from filmdub.workers.media_intake.probe import FFprobeParser, FFprobeError
    from filmdub.workers.media_intake.validator import MediaValidator, MediaValidationError
except ImportError:
    from filmdub.core.config import settings
    from filmdub.core.orchestrator_db import get_database_manager
    from filmdub.core.models import Base, Job, MediaAsset, Project
    from filmdub.workers.media_intake.filename_parser import parse_filename
    from filmdub.workers.media_intake.hashing import compute_sha256
    from filmdub.workers.media_intake.probe import FFprobeParser, FFprobeError
    from filmdub.workers.media_intake.validator import MediaValidator, MediaValidationError


# ==================== Filename Parser Tests ====================


def test_parse_filename_standard():
    """Test parsing standard filename format."""
    result = parse_filename("Breaking.Bad.S01E01.1080p.WEB-DL.mkv")
    assert result.season == 1
    assert result.episode == 1
    assert result.quality == "1080P"
    assert result.source == "WEB-DL"
    assert result.title_candidate == "Breaking Bad"
    assert result.confidence > 0.8


def test_parse_filename_alternative():
    """Test parsing alternative filename format."""
    result = parse_filename("Some.Show.1x05.720p.HDTV.x264-EVOLVE.mkv")
    assert result.season == 1
    assert result.episode == 5
    assert result.quality == "720P"
    assert result.source == "HDTV"
    assert result.codec == "X264"
    assert result.release_group == "EVOLVE"


def test_parse_filename_chinese():
    """Test parsing Chinese filename format."""
    result = parse_filename("绝命毒师 第01季 第01集.mkv")
    assert result.season == 1
    assert result.episode == 1


def test_parse_filename_no_season_episode():
    """Test parsing filename without season/episode."""
    result = parse_filename("Movie.2023.1080p.BluRay.mkv")
    assert result.season is None
    assert result.episode is None
    assert result.quality == "1080P"
    assert result.source == "BLURAY"


# ==================== Hashing Tests ====================


def test_compute_sha256():
    """Test SHA-256 computation."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Hello, World!")
        temp_path = Path(f.name)

    try:
        hash_value = compute_sha256(temp_path)
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)
    finally:
        temp_path.unlink()


def test_verify_sha256():
    """Test SHA-256 verification."""
    from filmdub.workers.media_intake.hashing import verify_sha256

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Hello, World!")
        temp_path = Path(f.name)

    try:
        hash_value = compute_sha256(temp_path)
        assert verify_sha256(temp_path, hash_value) is True
        assert verify_sha256(temp_path, "wrong" * 8) is False
    finally:
        temp_path.unlink()


# ==================== Validator Tests ====================


def test_validator_file_not_found():
    """Test validator with non-existent file."""
    validator = MediaValidator()
    with pytest.raises(MediaValidationError, match="FILE_NOT_FOUND"):
        validator.validate_file_exists(Path("/nonexistent/file.mkv"))


def test_validator_file_too_small():
    """Test validator with too small file."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("x")
        temp_path = Path(f.name)

    try:
        validator = MediaValidator()
        with pytest.raises(MediaValidationError, match="FILE_TOO_SMALL"):
            validator.validate_file_size(temp_path)
    finally:
        temp_path.unlink()


def test_validator_no_video_stream():
    """Test validator with no video stream."""
    validator = MediaValidator()
    with pytest.raises(MediaValidationError, match="NO_VIDEO_STREAM"):
        validator.validate_probe_result({"streams": [{"codec_type": "audio"}]})


def test_validator_no_audio_stream():
    """Test validator with no audio stream."""
    validator = MediaValidator()
    with pytest.raises(MediaValidationError, match="NO_AUDIO_STREAM"):
        validator.validate_probe_result({"streams": [{"codec_type": "video"}]})


# ==================== FFprobe Parser Tests ====================


def test_ffprobe_file_not_found():
    """Test FFprobe with non-existent file."""
    parser = FFprobeParser()
    with pytest.raises(FFprobeError, match="not found"):
        parser.probe(Path("/nonexistent/file.mkv"))


def test_ffprobe_get_video_streams():
    """Test extracting video streams."""
    parser = FFprobeParser()
    probe_data = {
        "streams": [
            {"codec_type": "video", "index": 0},
            {"codec_type": "audio", "index": 1},
        ]
    }
    video_streams = parser.get_video_streams(probe_data)
    assert len(video_streams) == 1
    assert video_streams[0]["index"] == 0


def test_ffprobe_get_audio_streams():
    """Test extracting audio streams."""
    parser = FFprobeParser()
    probe_data = {
        "streams": [
            {"codec_type": "video", "index": 0},
            {"codec_type": "audio", "index": 1},
            {"codec_type": "audio", "index": 2},
        ]
    }
    audio_streams = parser.get_audio_streams(probe_data)
    assert len(audio_streams) == 2


def test_ffprobe_select_default_video():
    """Test selecting default video stream."""
    parser = FFprobeParser()
    probe_data = {
        "streams": [
            {"codec_type": "video", "index": 0, "width": 1920, "height": 1080, "disposition": {"default": 0}},
            {"codec_type": "video", "index": 1, "width": 1280, "height": 720, "disposition": {"default": 1}},
        ]
    }
    default = parser.select_default_video_stream(probe_data)
    assert default is not None
    assert default["index"] == 1  # Has default disposition


def test_ffprobe_get_duration():
    """Test getting duration from probe data."""
    parser = FFprobeParser()
    probe_data = {
        "format": {"duration": "3612.45"},
        "streams": []
    }
    duration = parser.get_duration(probe_data)
    assert duration == 3612.45


# ==================== Integration Tests ====================


@pytest.mark.asyncio
async def test_create_project():
    """Test creating a project."""
    import uuid
    from filmdub.core.storage import StorageManager

    project_id = f"proj_{uuid.uuid4().hex[:12]}"

    db = get_database_manager(project_id)
    await db.initialize()

    try:
        async with db.session() as session:
            async with db.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            project = Project(
                id=project_id,
                title="Test Project",
                target_language="zh-CN",
                status="CREATED",
            )
            session.add(project)
            await session.commit()

            # Verify project was created
            result = await session.get(Project, project_id)
            assert result is not None
            assert result.title == "Test Project"

            # Verify storage directories were created
            storage = StorageManager(project_id)
            assert storage.get_project_dir().exists()
            assert storage.get_manifests_dir().exists()

    finally:
        await db.close()


@pytest.mark.asyncio
async def test_api_health_check():
    """Test API health check endpoint."""
    from filmdub.apps.api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_api_create_project():
    """Test API create project endpoint."""
    from filmdub.apps.api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/projects",
            json={"title": "Test Project", "target_language": "zh-CN"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Project"
        assert data["target_language"] == "zh-CN"
        assert data["status"] == "CREATED"
        assert "id" in data
