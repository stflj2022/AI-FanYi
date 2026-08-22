"""Tests for M09 Worker with adapter integration"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from filmdub.workers.voice_synthesis.m09_worker import M09Worker


@pytest.fixture
def m09_worker():
    """Create M09Worker instance"""
    return M09Worker(voice_backend="qwen")


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Create temporary output directory"""
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


class TestM09Worker:
    """Test M09Worker implementation"""

    def test_init(self):
        """Test worker initialization"""
        worker = M09Worker(voice_backend="qwen")
        assert worker.voice_config == {}
        assert worker.voice_adapter is not None

    @pytest.mark.asyncio
    async def test_synthesize_speech_success(self, m09_worker, tmp_output_dir):
        """Test successful speech synthesis"""
        output_path = tmp_output_dir / "test.wav"
        
        with patch.object(
            m09_worker.voice_adapter,
            "synthesize",
            return_value=output_path
        ):
            result = await m09_worker.synthesize_speech(
                text="Hello world",
                voice_id="voice-123",
                output_path=output_path,
                speed=1.0,
                pitch=1.0
            )
        
        assert result == output_path

    @pytest.mark.asyncio
    async def test_synthesize_batch_success(self, m09_worker, tmp_output_dir):
        """Test successful batch synthesis"""
        items = [
            {"text": "Hello", "voice_id": "voice-1", "output_filename": "speech_0001.wav"},
            {"text": "World", "voice_id": "voice-2", "output_filename": "speech_0002.wav"}
        ]
        
        mock_synthesize = AsyncMock(side_effect=lambda **kwargs: tmp_output_dir / kwargs["output_path"])
        
        with patch.object(
            m09_worker.voice_adapter,
            "synthesize",
            mock_synthesize
        ):
            results = await m09_worker.synthesize_batch(items, tmp_output_dir)
        
        assert len(results) == 2
        assert all(r["success"] for r in results)

    @pytest.mark.asyncio
    async def test_synthesize_batch_with_failure(self, m09_worker, tmp_output_dir):
        """Test batch synthesis with some failures"""
        items = [
            {"text": "Hello", "voice_id": "voice-1", "output_filename": "speech_0001.wav"},
            {"text": "World", "voice_id": "voice-2", "output_filename": "speech_0002.wav"}
        ]
        
        async def failing_synthesize(**kwargs):
            if "Hello" in kwargs["text"]:
                return tmp_output_dir / kwargs["output_path"]
            else:
                raise Exception("Synthesis failed")
        
        with patch.object(
            m09_worker.voice_adapter,
            "synthesize",
            side_effect=failing_synthesize
        ):
            results = await m09_worker.synthesize_batch(items, tmp_output_dir)
        
        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert "Synthesis failed" in results[1]["error"]

    @pytest.mark.asyncio
    async def test_list_available_voices(self, m09_worker):
        """Test listing available voices"""
        mock_voices = [
            {"voice_id": "voice-1", "name": "Voice 1"},
            {"voice_id": "voice-2", "name": "Voice 2"}
        ]
        
        with patch.object(
            m09_worker.voice_adapter,
            "list_voices",
            return_value=mock_voices
        ):
            voices = await m09_worker.list_available_voices()
        
        assert len(voices) == 2
        assert voices[0]["voice_id"] == "voice-1"

    @pytest.mark.asyncio
    async def test_get_voice_info(self, m09_worker):
        """Test getting voice info"""
        mock_voice_info = {
            "voice_id": "voice-1",
            "name": "Voice 1",
            "description": "Test voice"
        }
        
        with patch.object(
            m09_worker.voice_adapter,
            "get_voice",
            return_value=mock_voice_info
        ):
            voice_info = await m09_worker.get_voice_info("voice-1")
        
        assert voice_info is not None
        assert voice_info["voice_id"] == "voice-1"

    @pytest.mark.asyncio
    async def test_get_voice_info_not_found(self, m09_worker):
        """Test getting non-existent voice info"""
        with patch.object(
            m09_worker.voice_adapter,
            "get_voice",
            return_value=None
        ):
            voice_info = await m09_worker.get_voice_info("nonexistent")
        
        assert voice_info is None

    @pytest.mark.asyncio
    async def test_health_check(self, m09_worker):
        """Test health check"""
        with patch.object(
            m09_worker.voice_adapter,
            "health_check",
            return_value=True
        ):
            is_healthy = await m09_worker.health_check()
        
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_close(self, m09_worker):
        """Test worker cleanup"""
        with patch.object(m09_worker.voice_adapter, "close", new_callable=AsyncMock):
            await m09_worker.close()
