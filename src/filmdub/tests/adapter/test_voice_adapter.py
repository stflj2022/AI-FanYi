"""Tests for Voice Adapter"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from filmdub.adapter.voice import VoiceAdapter, QwenTTSAdapter


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient"""
    with patch("filmdub.adapter.voice.httpx.AsyncClient") as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client


@pytest.fixture
def voice_adapter(mock_httpx_client):
    """Create VoiceAdapter instance"""
    return VoiceAdapter(backend="qwen", base_url="http://localhost:8080")


@pytest.fixture
def sample_audio(tmp_path):
    """Create a sample audio file for testing"""
    audio_path = tmp_path / "test_audio.wav"
    audio_path.write_bytes(b"fake audio data")
    return audio_path


class TestQwenTTSAdapter:
    """Test QwenTTSAdapter implementation"""

    @pytest.mark.asyncio
    async def test_clone_voice_success(self, mock_httpx_client, sample_audio):
        """Test successful voice cloning"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"voice_id": "voice-123"}
        mock_httpx_client.post.return_value = mock_response

        adapter = QwenTTSAdapter(base_url="http://localhost:8080")
        voice_id = await adapter.clone_voice(
            name="test-voice",
            reference_audio_path=sample_audio,
            description="Test voice"
        )

        assert voice_id == "voice-123"
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_clone_voice_file_not_found(self):
        """Test cloning with non-existent file"""
        adapter = QwenTTSAdapter(base_url="http://localhost:8080")
        with pytest.raises(FileNotFoundError):
            await adapter.clone_voice(
                name="test-voice",
                reference_audio_path=Path("/nonexistent/audio.wav")
            )

    @pytest.mark.asyncio
    async def test_list_voices_success(self, mock_httpx_client):
        """Test listing voices successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "voices": [
                {"voice_id": "voice-1", "name": "Voice 1"},
                {"voice_id": "voice-2", "name": "Voice 2"}
            ]
        }
        mock_httpx_client.get.return_value = mock_response

        adapter = QwenTTSAdapter(base_url="http://localhost:8080")
        voices = await adapter.list_voices()

        assert len(voices) == 2
        assert voices[0]["voice_id"] == "voice-1"

    @pytest.mark.asyncio
    async def test_get_voice_success(self, mock_httpx_client):
        """Test getting voice details successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "voice_id": "voice-1",
            "name": "Voice 1",
            "description": "Test voice"
        }
        mock_httpx_client.get.return_value = mock_response

        adapter = QwenTTSAdapter(base_url="http://localhost:8080")
        voice = await adapter.get_voice("voice-1")

        assert voice is not None
        assert voice["voice_id"] == "voice-1"

    @pytest.mark.asyncio
    async def test_get_voice_not_found(self, mock_httpx_client):
        """Test getting non-existent voice"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_httpx_client.get.return_value = mock_response

        adapter = QwenTTSAdapter(base_url="http://localhost:8080")
        voice = await adapter.get_voice("nonexistent")

        assert voice is None

    @pytest.mark.asyncio
    async def test_delete_voice_success(self, mock_httpx_client):
        """Test deleting voice successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx_client.delete.return_value = mock_response

        adapter = QwenTTSAdapter(base_url="http://localhost:8080")
        result = await adapter.delete_voice("voice-1")

        assert result is True

    @pytest.mark.asyncio
    async def test_synthesize_success(self, mock_httpx_client, tmp_path):
        """Test successful synthesis"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake audio data"
        mock_httpx_client.post.return_value = mock_response

        adapter = QwenTTSAdapter(base_url="http://localhost:8080")
        output_path = tmp_path / "output.wav"

        result = await adapter.synthesize(
            text="Hello world",
            voice_id="voice-1",
            output_path=output_path
        )

        assert result == output_path
        assert output_path.exists()
        assert output_path.read_bytes() == b"fake audio data"

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_httpx_client):
        """Test successful health check"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx_client.get.return_value = mock_response

        adapter = QwenTTSAdapter(base_url="http://localhost:8080")
        is_healthy = await adapter.health_check()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_httpx_client):
        """Test health check when service is down"""
        mock_httpx_client.get.side_effect = Exception("Connection refused")

        adapter = QwenTTSAdapter(base_url="http://localhost:8080")
        is_healthy = await adapter.health_check()

        assert is_healthy is False


class TestVoiceAdapter:
    """Test VoiceAdapter factory"""

    def test_unsupported_backend(self):
        """Test that unsupported backend raises error"""
        with pytest.raises(ValueError, match="Unsupported voice backend"):
            VoiceAdapter(backend="invalid")

    @pytest.mark.asyncio
    async def test_health_check(self, voice_adapter, mock_httpx_client):
        """Test health check through factory"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx_client.get.return_value = mock_response

        is_healthy = await voice_adapter.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_close(self, voice_adapter, mock_httpx_client):
        """Test closing adapter"""
        await voice_adapter.close()
        mock_httpx_client.aclose.assert_called_once()
