"""Tests for M05 Worker with adapter integration"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from filmdub.workers.audio_scene_analysis.m05_worker import M05Worker


@pytest.fixture
def sample_audio(tmp_path):
    """Create a sample audio file for testing"""
    audio_path = tmp_path / "test_audio.wav"
    with audio_path.open("wb") as f:
        f.write(b"RIFF" + b"\x00" * 36 + b"WAVE" + b"\x00" * 1000)
    return audio_path


@pytest.fixture
def m05_worker():
    """Create M05Worker instance"""
    return M05Worker(asr_backend="faster-whisper")


class TestM05Worker:
    """Test M05Worker implementation"""

    def test_init(self):
        """Test worker initialization"""
        worker = M05Worker(asr_backend="faster-whisper")
        assert worker.asr_config == {}
        assert worker.asr_adapter is not None

    @pytest.mark.asyncio
    async def test_transcribe_audio_missing_file(self, m05_worker):
        """Test transcription with missing file"""
        with pytest.raises(FileNotFoundError):
            await m05_worker.transcribe_audio(Path("/nonexistent/audio.wav"))

    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self, m05_worker, sample_audio):
        """Test successful audio transcription"""
        mock_result = {
            "text": "Hello world this is a test",
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello world"},
                {"start": 2.5, "end": 5.0, "text": "this is a test"}
            ],
            "language": "en",
            "language_probability": 0.95
        }
        
        with patch.object(
            m05_worker.asr_adapter,
            "transcribe",
            return_value=mock_result
        ):
            result = await m05_worker.transcribe_audio(sample_audio, language="en")
        
        assert result["text"] == "Hello world this is a test"
        assert len(result["segments"]) == 2
        assert result["language"] == "en"

    @pytest.mark.asyncio
    async def test_transcribe_with_speakers_success(self, m05_worker, sample_audio):
        """Test successful transcription with speaker diarization"""
        mock_segments = [
            {"start": 0.0, "end": 2.5, "text": "Hello world", "speaker": "SPEAKER_00"},
            {"start": 2.5, "end": 5.0, "text": "This is a test", "speaker": "SPEAKER_01"}
        ]
        
        with patch.object(
            m05_worker.asr_adapter,
            "transcribe_with_speakers",
            return_value=mock_segments
        ):
            segments = await m05_worker.transcribe_with_speakers(sample_audio, num_speakers=2)
        
        assert len(segments) == 2
        assert segments[0]["speaker"] == "SPEAKER_00"
        assert segments[1]["speaker"] == "SPEAKER_01"

    @pytest.mark.asyncio
    async def test_analyze_dialogue_with_speakers(self, m05_worker, sample_audio):
        """Test dialogue analysis with speakers"""
        mock_segments = [
            {"start": 0.0, "end": 2.5, "text": "Hello", "speaker": "SPEAKER_00"},
            {"start": 2.5, "end": 5.0, "text": "Hi there", "speaker": "SPEAKER_01"}
        ]
        
        with patch.object(
            m05_worker.asr_adapter,
            "transcribe_with_speakers",
            return_value=mock_segments
        ):
            result = await m05_worker.analyze_dialogue(
                sample_audio,
                with_speakers=True,
                language="en"
            )
        
        assert result["with_speakers"] is True
        assert result["num_speakers"] == 2
        assert len(result["segments"]) == 2
        assert result["total_duration"] == 5.0

    @pytest.mark.asyncio
    async def test_analyze_dialogue_without_speakers(self, m05_worker, sample_audio):
        """Test dialogue analysis without speakers"""
        mock_transcription = {
            "text": "Hello world this is a test",
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello world"},
                {"start": 2.5, "end": 5.0, "text": "this is a test"}
            ],
            "language": "en"
        }
        
        with patch.object(
            m05_worker.asr_adapter,
            "transcribe",
            return_value=mock_transcription
        ):
            result = await m05_worker.analyze_dialogue(
                sample_audio,
                with_speakers=False,
                language="en"
            )
        
        assert result["with_speakers"] is False
        assert result["language"] == "en"
        assert result["full_text"] == "Hello world this is a test"

    @pytest.mark.asyncio
    async def test_close(self, m05_worker):
        """Test worker cleanup"""
        # Mock close method if it exists
        if hasattr(m05_worker.asr_adapter, 'close'):
            with patch.object(m05_worker.asr_adapter, "close", new_callable=AsyncMock):
                await m05_worker.close()
        else:
            await m05_worker.close()  # Should not raise error
