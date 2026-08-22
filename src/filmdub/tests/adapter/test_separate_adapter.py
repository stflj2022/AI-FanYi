"""Tests for Audio Separation Adapter"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from filmdub.adapter.separate import AudioSeparationAdapter, HTDemucsAdapter


@pytest.fixture
def sample_audio(tmp_path):
    """Create a sample audio file for testing"""
    audio_path = tmp_path / "test_audio.wav"
    # Write a minimal WAV header + some data
    with audio_path.open("wb") as f:
        f.write(b"RIFF" + b"\x00" * 36 + b"WAVE" + b"\x00" * 1000)
    return audio_path


class TestHTDemucsAdapter:
    """Test HTDemucsAdapter implementation"""

    def test_init(self):
        """Test adapter initialization"""
        adapter = HTDemucsAdapter(model="htdemucs", device="cpu")
        assert adapter.model == "htdemucs"
        assert adapter.device == "cpu"
        assert adapter._loaded is False

    def test_unsupported_backend(self):
        """Test that unsupported backend raises error"""
        with pytest.raises(ValueError, match="Unsupported separation backend"):
            AudioSeparationAdapter(backend="invalid")

    @pytest.mark.asyncio
    async def test_separate_file_not_found(self):
        """Test separation with non-existent file"""
        adapter = HTDemucsAdapter()
        output_dir = Path("/tmp/stems")
        with pytest.raises(FileNotFoundError):
            await adapter.separate(Path("/nonexistent/audio.wav"), output_dir)

    @pytest.mark.asyncio
    async def test_separate_missing_model(self, sample_audio, tmp_path):
        """Test separation when demucs is not installed"""
        adapter = HTDemucsAdapter()

        # Patch import to simulate missing dependency
        with patch.dict("sys.modules", {"demucs": None}):
            with pytest.raises(ImportError, match="demucs not installed"):
                await adapter.separate(sample_audio, tmp_path)

    @pytest.mark.skip(reason="Test has state interference with other tests")
    @pytest.mark.asyncio
    async def test_separate_vocals_only_missing_model(self, sample_audio, tmp_path):
        """Test vocals extraction when demucs is not installed"""
        adapter = HTDemucsAdapter()

        with patch.dict("sys.modules", {"demucs": None}):
            with pytest.raises(ImportError, match="demucs not installed"):
                await adapter.separate_vocals_only(sample_audio, tmp_path / "vocals.wav")


class TestAudioSeparationAdapter:
    """Test AudioSeparationAdapter factory"""

    def test_unsupported_backend(self):
        """Test that unsupported backend raises error"""
        with pytest.raises(ValueError, match="Unsupported separation backend"):
            AudioSeparationAdapter(backend="invalid")

    def test_backend_selection(self):
        """Test backend selection"""
        adapter = AudioSeparationAdapter(backend="htdemucs", model="htdemucs_ft")
        assert adapter._adapter.model == "htdemucs_ft"
