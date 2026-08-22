"""Tests for M02 Worker with adapter integration"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from filmdub.workers.research.m02_worker import M02Worker


@pytest.fixture
def sample_audio(tmp_path):
    """Create a sample audio file for testing"""
    audio_path = tmp_path / "test_audio.wav"
    # Write a minimal WAV header + some data
    with audio_path.open("wb") as f:
        f.write(b"RIFF" + b"\x00" * 36 + b"WAVE" + b"\x00" * 1000)
    return audio_path


@pytest.fixture
def m02_worker():
    """Create M02Worker instance"""
    return M02Worker(separation_backend="htdemucs")


class TestM02Worker:
    """Test M02Worker implementation"""

    def test_init(self):
        """Test worker initialization"""
        worker = M02Worker(separation_backend="htdemucs")
        assert worker.separation_config == {}
        assert worker.separation_adapter is not None

    @pytest.mark.asyncio
    async def test_analyze_audio_missing_file(self, m02_worker):
        """Test analysis with missing file"""
        with pytest.raises(FileNotFoundError):
            await m02_worker.analyze_audio(Path("/nonexistent/audio.wav"))

    @pytest.mark.asyncio
    async def test_analyze_audio_vocals_only(self, m02_worker, sample_audio, tmp_path):
        """Test audio analysis extracting vocals only"""
        output_dir = tmp_path / "output"
        
        # Mock the separate_vocals_only method
        with patch.object(
            m02_worker.separation_adapter,
            "separate_vocals_only",
            return_value=output_dir / "vocals.wav"
        ):
            result = await m02_worker.analyze_audio(
                sample_audio,
                output_dir=output_dir,
                extract_vocals_only=True
            )
        
        assert result["extract_vocals_only"] is True
        assert "vocals" in result["stems"]
        assert result["audio_path"] == str(sample_audio)

    @pytest.mark.asyncio
    async def test_analyze_audio_all_stems(self, m02_worker, sample_audio, tmp_path):
        """Test audio analysis extracting all stems"""
        output_dir = tmp_path / "output"
        
        # Mock the separate method
        mock_stems = {
            "vocals": output_dir / "vocals.wav",
            "drums": output_dir / "drums.wav",
            "bass": output_dir / "bass.wav",
            "other": output_dir / "other.wav"
        }
        
        with patch.object(
            m02_worker.separation_adapter,
            "separate",
            return_value=mock_stems
        ):
            result = await m02_worker.analyze_audio(
                sample_audio,
                output_dir=output_dir,
                extract_vocals_only=False
            )
        
        assert result["extract_vocals_only"] is False
        assert len(result["stems"]) == 4
        assert "vocals" in result["stems"]
        assert "drums" in result["stems"]

    @pytest.mark.asyncio
    async def test_close(self, m02_worker):
        """Test worker cleanup"""
        # Mock close method if it exists
        if hasattr(m02_worker.separation_adapter, 'close'):
            with patch.object(m02_worker.separation_adapter, "close", new_callable=AsyncMock):
                await m02_worker.close()
        else:
            await m02_worker.close()  # Should not raise error
