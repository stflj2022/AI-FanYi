"""
Voice Adapter for qwen-tts integration

Provides a unified interface for voice cloning and synthesis
that can be used by M04 (character DB) and M09 (voice synthesis).
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pathlib import Path
import httpx
import logging

logger = logging.getLogger(__name__)


class VoiceAdapterInterface(ABC):
    """Abstract interface for voice operations"""

    @abstractmethod
    async def clone_voice(
        self,
        name: str,
        reference_audio_path: Path,
        description: Optional[str] = None
    ) -> str:
        """Clone a voice from reference audio, returns voice_id"""
        pass

    @abstractmethod
    async def list_voices(self) -> List[Dict[str, Any]]:
        """List all available voices"""
        pass

    @abstractmethod
    async def get_voice(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get voice details by ID"""
        pass

    @abstractmethod
    async def delete_voice(self, voice_id: str) -> bool:
        """Delete a voice by ID"""
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
        speed: float = 1.0,
        pitch: float = 1.0
    ) -> Path:
        """Synthesize speech with given voice, returns output path"""
        pass


class QwenTTSAdapter(VoiceAdapterInterface):
    """qwen-tts service adapter implementation

    Supports both custom API and OpenAI-compatible API endpoints.
    """

    def __init__(self, base_url: str = "http://localhost:8080", timeout: int = 300, use_openai_api: bool = True):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.use_openai_api = use_openai_api
        self.client = httpx.AsyncClient(timeout=timeout)
        self._model_id = None  # Will be fetched from /v1/models

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def clone_voice(
        self,
        name: str,
        reference_audio_path: Path,
        description: Optional[str] = None
    ) -> str:
        """
        Clone voice using qwen-tts service

        Args:
            name: Name for the cloned voice
            reference_audio_path: Path to reference audio file
            description: Optional description

        Returns:
            voice_id: ID of the cloned voice

        Raises:
            httpx.HTTPError: If API call fails
        """
        if not reference_audio_path.exists():
            raise FileNotFoundError(f"Reference audio not found: {reference_audio_path}")

        # Prepare files and data
        files = {
            "audio": (reference_audio_path.name, reference_audio_path.open("rb"), "audio/wav")
        }
        data = {
            "name": name,
            "description": description or f"Cloned voice: {name}"
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/voices/clone",
                files=files,
                data=data
            )
            response.raise_for_status()
            result = response.json()
            voice_id = result.get("voice_id")
            if not voice_id:
                raise ValueError(f"No voice_id in response: {result}")
            logger.info(f"Cloned voice '{name}' with ID: {voice_id}")
            return voice_id
        except httpx.HTTPError as e:
            logger.error(f"Failed to clone voice '{name}': {e}")
            raise

    async def list_voices(self) -> List[Dict[str, Any]]:
        """List all available voices from qwen-tts service"""
        try:
            response = await self.client.get(f"{self.base_url}/api/voices")
            response.raise_for_status()
            result = response.json()
            voices = result.get("voices", [])
            logger.info(f"Listed {len(voices)} voices")
            return voices
        except httpx.HTTPError as e:
            logger.error(f"Failed to list voices: {e}")
            raise

    async def get_voice(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get voice details by ID"""
        try:
            response = await self.client.get(f"{self.base_url}/api/voices/{voice_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            result = response.json()
            return result
        except httpx.HTTPError as e:
            logger.error(f"Failed to get voice {voice_id}: {e}")
            raise

    async def delete_voice(self, voice_id: str) -> bool:
        """Delete a voice by ID"""
        try:
            response = await self.client.delete(f"{self.base_url}/api/voices/{voice_id}")
            if response.status_code == 404:
                return False
            response.raise_for_status()
            logger.info(f"Deleted voice {voice_id}")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to delete voice {voice_id}: {e}")
            raise

    async def _get_model_id(self) -> str:
        """Get available model ID from the service"""
        if self._model_id is None:
            try:
                response = await self.client.get(f"{self.base_url}/v1/models", timeout=5)
                response.raise_for_status()
                models_data = response.json()
                if "data" in models_data and len(models_data["data"]) > 0:
                    self._model_id = models_data["data"][0]["id"]
                    logger.info(f"Using model: {self._model_id}")
                else:
                    self._model_id = "default"
            except Exception as e:
                logger.warning(f"Failed to get model ID, using default: {e}")
                self._model_id = "default"
        return self._model_id

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
        speed: float = 1.0,
        pitch: float = 1.0
    ) -> Path:
        """
        Synthesize speech using qwen-tts service

        Args:
            text: Text to synthesize
            voice_id: Voice ID to use (may be ignored if using OpenAI API)
            output_path: Path to save output audio
            speed: Speed factor (default 1.0)
            pitch: Pitch factor (default 1.0)

        Returns:
            output_path: Path to synthesized audio file

        Raises:
            httpx.HTTPError: If API call fails
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.use_openai_api:
            # Use OpenAI-compatible API endpoint
            model_id = await self._get_model_id()
            payload = {
                "input": text,
                "model": model_id,
                "voice": voice_id if voice_id != "default" else None
            }
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            endpoint = f"{self.base_url}/v1/audio/speech"
            # OpenAI API returns MP3 format
            actual_output_path = output_path.with_suffix('.mp3')
        else:
            # Use custom API endpoint
            payload = {
                "text": text,
                "voice_id": voice_id,
                "speed": speed,
                "pitch": pitch
            }
            endpoint = f"{self.base_url}/api/synthesize"
            actual_output_path = output_path

        try:
            response = await self.client.post(endpoint, json=payload)
            response.raise_for_status()

            # Save audio file
            with actual_output_path.open("wb") as f:
                f.write(response.content)

            logger.info(f"Synthesized {len(text)} chars with voice {voice_id} -> {actual_output_path}")
            return actual_output_path
        except httpx.HTTPError as e:
            logger.error(f"Failed to synthesize with voice {voice_id}: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if qwen-tts service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"qwen-tts health check failed: {e}")
            return False


class VoiceAdapter(VoiceAdapterInterface):
    """
    Factory for creating voice adapters

    Automatically selects QwenTTSAdapter if configured,
    can be extended for other TTS backends.
    """

    def __init__(self, backend: str = "qwen", **kwargs):
        if backend == "qwen":
            self._adapter = QwenTTSAdapter(**kwargs)
        else:
            raise ValueError(f"Unsupported voice backend: {backend}")

    async def clone_voice(
        self,
        name: str,
        reference_audio_path: Path,
        description: Optional[str] = None
    ) -> str:
        return await self._adapter.clone_voice(name, reference_audio_path, description)

    async def list_voices(self) -> List[Dict[str, Any]]:
        return await self._adapter.list_voices()

    async def get_voice(self, voice_id: str) -> Optional[Dict[str, Any]]:
        return await self._adapter.get_voice(voice_id)

    async def delete_voice(self, voice_id: str) -> bool:
        return await self._adapter.delete_voice(voice_id)

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
        speed: float = 1.0,
        pitch: float = 1.0
    ) -> Path:
        return await self._adapter.synthesize(text, voice_id, output_path, speed, pitch)

    async def close(self):
        """Close adapter resources"""
        if hasattr(self._adapter, "close"):
            await self._adapter.close()

    async def health_check(self) -> bool:
        """Check if backend service is healthy"""
        if hasattr(self._adapter, "health_check"):
            return await self._adapter.health_check()
        return True
