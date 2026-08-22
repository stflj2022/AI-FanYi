"""Tests for M04 Worker with adapter integration"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from filmdub.workers.character_db.m04_worker import M04Worker


@pytest.fixture
def sample_audio(tmp_path):
    """Create a sample audio file for testing"""
    audio_path = tmp_path / "test_audio.wav"
    with audio_path.open("wb") as f:
        f.write(b"RIFF" + b"\x00" * 36 + b"WAVE" + b"\x00" * 1000)
    return audio_path


@pytest.fixture
def m04_worker(tmp_path):
    """Create M04Worker instance"""
    voices_dir = tmp_path / "voices"
    return M04Worker(voice_backend="qwen", voices_dir=voices_dir)


class TestM04Worker:
    """Test M04Worker implementation"""

    def test_init(self, tmp_path):
        """Test worker initialization"""
        voices_dir = tmp_path / "voices"
        worker = M04Worker(voice_backend="qwen", voices_dir=voices_dir)
        assert worker.voices_dir == voices_dir
        assert voices_dir.exists()

    @pytest.mark.asyncio
    async def test_clone_character_voice_success(self, m04_worker, sample_audio):
        """Test successful voice cloning"""
        # Mock clone_voice
        with patch.object(
            m04_worker.voice_adapter,
            "clone_voice",
            return_value="voice-123"
        ):
            result = await m04_worker.clone_character_voice(
                character_id="char-001",
                character_name="Walter",
                reference_audio_path=sample_audio,
                description="Main character voice"
            )
        
        assert result["voice_id"] == "voice-123"
        assert result["character_id"] == "char-001"
        assert result["character_name"] == "Walter"
        
        # Check voice mapping file was created
        voice_mapping_path = m04_worker.voices_dir / "char-001_voice.json"
        assert voice_mapping_path.exists()

    @pytest.mark.asyncio
    async def test_clone_character_voice_missing_file(self, m04_worker):
        """Test voice cloning with missing file"""
        with pytest.raises(FileNotFoundError):
            await m04_worker.clone_character_voice(
                character_id="char-001",
                character_name="Walter",
                reference_audio_path=Path("/nonexistent/audio.wav")
            )

    @pytest.mark.asyncio
    async def test_get_character_voice(self, m04_worker, sample_audio):
        """Test getting character voice info"""
        # First clone a voice
        with patch.object(
            m04_worker.voice_adapter,
            "clone_voice",
            return_value="voice-123"
        ):
            await m04_worker.clone_character_voice(
                character_id="char-001",
                character_name="Walter",
                reference_audio_path=sample_audio
            )
        
        # Get voice info
        voice_info = await m04_worker.get_character_voice("char-001")
        
        assert voice_info is not None
        assert voice_info["voice_id"] == "voice-123"
        assert voice_info["character_name"] == "Walter"

    @pytest.mark.asyncio
    async def test_get_character_voice_not_found(self, m04_worker):
        """Test getting non-existent character voice"""
        voice_info = await m04_worker.get_character_voice("nonexistent")
        assert voice_info is None

    @pytest.mark.asyncio
    async def test_list_all_voices(self, m04_worker):
        """Test listing all voices"""
        mock_voices = [
            {"voice_id": "voice-1", "name": "Voice 1"},
            {"voice_id": "voice-2", "name": "Voice 2"}
        ]
        
        with patch.object(
            m04_worker.voice_adapter,
            "list_voices",
            return_value=mock_voices
        ):
            voices = await m04_worker.list_all_voices()
        
        assert len(voices) == 2
        assert voices[0]["voice_id"] == "voice-1"

    @pytest.mark.asyncio
    async def test_delete_character_voice(self, m04_worker, sample_audio):
        """Test deleting character voice"""
        # First clone a voice
        with patch.object(
            m04_worker.voice_adapter,
            "clone_voice",
            return_value="voice-123"
        ):
            await m04_worker.clone_character_voice(
                character_id="char-001",
                character_name="Walter",
                reference_audio_path=sample_audio
            )
        
        # Delete voice
        with patch.object(
            m04_worker.voice_adapter,
            "delete_voice",
            return_value=True
        ):
            success = await m04_worker.delete_character_voice("char-001")
        
        assert success is True
        
        # Check voice mapping file was deleted
        voice_mapping_path = m04_worker.voices_dir / "char-001_voice.json"
        assert not voice_mapping_path.exists()

    @pytest.mark.asyncio
    async def test_synthesize_character_speech(self, m04_worker, sample_audio, tmp_path):
        """Test synthesizing character speech"""
        # First clone a voice
        with patch.object(
            m04_worker.voice_adapter,
            "clone_voice",
            return_value="voice-123"
        ):
            await m04_worker.clone_character_voice(
                character_id="char-001",
                character_name="Walter",
                reference_audio_path=sample_audio
            )
        
        output_path = tmp_path / "output.wav"
        
        with patch.object(
            m04_worker.voice_adapter,
            "synthesize",
            return_value=output_path
        ):
            result = await m04_worker.synthesize_character_speech(
                character_id="char-001",
                text="Hello world",
                output_path=output_path,
                speed=1.0,
                pitch=1.0
            )
        
        assert result == output_path

    @pytest.mark.asyncio
    async def test_health_check(self, m04_worker):
        """Test health check"""
        with patch.object(
            m04_worker.voice_adapter,
            "health_check",
            return_value=True
        ):
            is_healthy = await m04_worker.health_check()
        
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_close(self, m04_worker):
        """Test worker cleanup"""
        with patch.object(m04_worker.voice_adapter, "close", new_callable=AsyncMock):
            await m04_worker.close()
