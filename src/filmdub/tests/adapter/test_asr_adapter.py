"""Tests for ASR Adapter"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from filmdub.adapter.asr import ASRAdapter, FasterWhisperASRAdapter


@pytest.fixture
def sample_audio(tmp_path):
    """Create a sample audio file for testing"""
    audio_path = tmp_path / "test_audio.wav"
    # Write a minimal WAV header + some data
    with audio_path.open("wb") as f:
        f.write(b"RIFF" + b"\x00" * 36 + b"WAVE" + b"\x00" * 100)
    return audio_path


class TestFasterWhisperASRAdapter:
    """Test FasterWhisperASRAdapter implementation"""

    def test_init(self):
        """Test adapter initialization"""
        adapter = FasterWhisperASRAdapter(model_size="large-v3", device="cpu")
        assert adapter.model_size == "large-v3"
        assert adapter.device == "cpu"
        assert adapter._model is None

    def test_unsupported_backend(self):
        """Test that unsupported backend raises error"""
        with pytest.raises(ValueError, match="Unsupported ASR backend"):
            ASRAdapter(backend="invalid")

    @pytest.mark.asyncio
    async def test_transcribe_file_not_found(self):
        """Test transcription with non-existent file"""
        adapter = FasterWhisperASRAdapter()
        with pytest.raises(FileNotFoundError):
            await adapter.transcribe(Path("/nonexistent/audio.wav"))

    @pytest.mark.skip(reason="Test has state interference with other tests")
    @pytest.mark.asyncio
    async def test_transcribe_with_missing_model(self, sample_audio):
        """Test transcription when faster-whisper is not installed"""
        adapter = FasterWhisperASRAdapter()

        # Patch import to simulate missing dependency
        with patch.dict("sys.modules", {"faster_whisper": None}):
            with pytest.raises(ImportError, match="faster-whisper not installed"):
                await adapter.transcribe(sample_audio)

    @pytest.mark.skip(reason="Test has state interference with other tests")
    @pytest.mark.asyncio
    async def test_transcribe_with_speakers_missing_model(self, sample_audio):
        """Test speaker diarization when pyannote is not available"""
        # Mock the transcribe method
        adapter = FasterWhisperASRAdapter()

        mock_result = {
            "text": "Hello world",
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello world"}
            ],
            "language": "en",
            "language_probability": 0.95
        }

        with patch.object(adapter, "transcribe", return_value=mock_result):
            # Mock pyannote import failure
            with patch.dict("sys.modules", {"pyannote": None}):
                result = await adapter.transcribe_with_speakers(sample_audio)

        assert len(result) == 1
        assert result[0]["speaker"] == "SPEAKER_00"
        assert result[0]["text"] == "Hello world"


class TestASRAdapter:
    """Test ASRAdapter factory"""

    def test_unsupported_backend(self):
        """Test that unsupported backend raises error"""
        with pytest.raises(ValueError, match="Unsupported ASR backend"):
            ASRAdapter(backend="invalid")

    def test_backend_selection(self):
        """Test backend selection"""
        adapter = ASRAdapter(backend="faster-whisper", model_size="large-v3")
        assert adapter._adapter.model_size == "large-v3"
