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
import numpy as np

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

    def __init__(self, base_url: str = "http://localhost:8081", timeout: int = 300, use_openai_api: bool = True):
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
                "voice": voice_id if voice_id != "default" else None,
                "language": "auto",
                "response_format": "wav"
            }
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            endpoint = f"{self.base_url}/v1/audio/speech"
            # qwen-tts (C++ server) returns WAV format; ignore OpenAI MP3 assumption
            actual_output_path = output_path.with_suffix('.wav')
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

    def model_info(self) -> Dict[str, Any]:
        """返回 qwen-tts 后端模型信息（进入 Artifact 可复现）"""
        return {
            "backend": "qwen",
            "model_name": "qwen-tts",
            "model_version": self._model_id,
            "base_url": self.base_url,
        }


class LocalVoiceAdapter(VoiceAdapterInterface):
    """
    本地 TTS 模型适配器基类（CosyVoice / F5-TTS）

    统一实现 VoiceAdapterInterface.synthesize：懒加载模型 → 同步推理（放入线程）→
    numpy 音频落盘为 WAV → 返回输出路径。提供 model_info() 记录模型版本/参数（可复现）。
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: Optional[str] = None,
        device: str = "cpu",
        sample_rate: int = 22050,
    ):
        self.model_path = model_path
        self.model_name = model_name or self.__class__.__name__.replace("Adapter", "")
        self.device = device
        self.sample_rate = sample_rate
        self._model = None
        self._model_version = None
        self._load_error = None

    # ------------------------------------------------------------------
    # 子类实现
    # ------------------------------------------------------------------
    def _load_model(self):
        """加载本地模型，返回模型对象。未安装依赖时抛出 ImportError。"""
        raise NotImplementedError

    def _run_inference(
        self, model, text: str, voice_id: str, speed: float, pitch: float, kwargs: Dict[str, Any]
    ) -> Any:
        """执行同步推理，返回 (audio: np.ndarray, sample_rate: int)。"""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 懒加载
    # ------------------------------------------------------------------
    async def _get_model(self):
        if self._model is None:
            import asyncio
            self._model = await asyncio.to_thread(self._load_model)
            # 兜底：若 _load_model 未设置版本，则从模型对象读取
            if self._model_version is None:
                self._model_version = getattr(self._model, "version", None)
        return self._model

    # ------------------------------------------------------------------
    # VoiceAdapterInterface 实现
    # ------------------------------------------------------------------
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
        speed: float = 1.0,
        pitch: float = 1.0,
        **kwargs
    ) -> Path:
        """
        本地模型合成语音并落盘 WAV

        Args:
            text: 合成文本
            voice_id: 音色 ID（本地模型下为参考音频路径或提示文本 ID）
            output_path: 输出路径（自动补 .wav 后缀）
            speed: 语速因子
            pitch: 音高因子（本地模型不原生支持时忽略，由 M10 处理）
            **kwargs: prompt_text / reference_audio 等透传参数

        Returns:
            输出 WAV 文件路径
        """
        model = await self._get_model()
        import asyncio
        audio, sr = await asyncio.to_thread(
            self._run_inference, model, text, voice_id, speed, pitch, kwargs
        )
        output_path = self._save_audio(audio, sr, output_path)
        logger.info(f"[{self.model_name}] synthesized {len(text)} chars -> {output_path}")
        return output_path

    async def clone_voice(self, name, reference_audio_path, description=None) -> str:
        # 本地零样本/小样本克隆：以参考音频路径作为音色 ID
        return str(reference_audio_path)

    async def list_voices(self) -> List[Dict[str, Any]]:
        return [
            {
                "voice_id": f"{self.model_name}-default",
                "name": f"{self.model_name} Default",
            }
        ]

    async def get_voice(self, voice_id: str) -> Optional[Dict[str, Any]]:
        if not voice_id:
            return None
        return {"voice_id": voice_id, "name": voice_id, "model": self.model_name}

    async def delete_voice(self, voice_id: str) -> bool:
        return False

    async def close(self):
        self._model = None

    async def health_check(self) -> bool:
        try:
            await self._get_model()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------
    def model_info(self) -> Dict[str, Any]:
        """返回模型版本/参数信息（用于进入 Artifact，保证可复现）"""
        return {
            "backend": self.model_name,
            "model_name": self.model_name,
            "model_version": self._model_version,
            "model_path": self.model_path,
            "device": self.device,
            "sample_rate": self.sample_rate,
        }

    @staticmethod
    def _save_audio(audio, sample_rate: int, output_path: Path) -> Path:
        """numpy 音频落盘为 WAV（soundfile 优先，wave 回退）"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio = np.asarray(audio).squeeze()
        if audio.ndim > 1:
            # 多声道 → 取均值转单声道
            audio = audio.mean(axis=-1)
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        elif np.issubdtype(audio.dtype, np.integer):
            audio = audio.astype(np.float32) / (np.iinfo(audio.dtype).max + 1.0)
        audio = np.clip(audio, -1.0, 1.0)

        if output_path.suffix.lower() != ".wav":
            output_path = output_path.with_suffix(".wav")

        try:
            import soundfile as sf
            sf.write(str(output_path), audio, sample_rate)
        except ImportError:
            pcm = (audio * 32767.0).astype(np.int16)
            import wave
            with wave.open(str(output_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(pcm.tobytes())
        return output_path


class CosyVoiceAdapter(LocalVoiceAdapter):
    """CosyVoice 本地 TTS 适配器（zero-shot 克隆 + 语音合成）"""

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: Optional[str] = "CosyVoice-300M",
        device: str = "cpu",
        sample_rate: int = 22050,
    ):
        super().__init__(
            model_path=model_path,
            model_name=model_name or "CosyVoice-300M",
            device=device,
            sample_rate=sample_rate,
        )

    def _load_model(self):
        try:
            from cosyvoice.cli.cosyvoice import CosyVoice  # type: ignore
        except ImportError as e:
            raise ImportError(
                "CosyVoice 未安装。请先安装 CosyVoice 及其依赖（torch）再使用该后端。"
            ) from e
        model = CosyVoice(self.model_path or self.model_name)
        self._model_version = getattr(model, "version", "unknown")
        return model

    def _run_inference(
        self, model, text: str, voice_id: str, speed: float, pitch: float, kwargs: Dict[str, Any]
    ) -> Any:
        import numpy as np  # noqa: F401 (本地引用保持一致性)

        prompt_text = kwargs.get("prompt_text") or voice_id or ""
        reference_audio = kwargs.get("reference_audio") or kwargs.get("prompt_speech")

        if reference_audio:
            # 参考音频存在：zero-shot 音色克隆
            result = model.inference_zero_shot(
                tts_text=text,
                prompt_text=prompt_text,
                prompt_speech_16k=reference_audio,
            )
        else:
            # 无参考音频：直接语音合成
            result = model.inference_speech(tts_text=text)

        # CosyVoice 返回生成器，取第一段
        try:
            chunk = next(iter(result))
        except StopIteration:
            raise RuntimeError("CosyVoice 未返回任何音频")

        audio = chunk["tts_speech"]
        if hasattr(audio, "numpy"):
            audio = audio.numpy()
        sr = int(chunk.get("sample_rate", self.sample_rate))
        return audio, sr


class F5TTSAdapter(LocalVoiceAdapter):
    """F5-TTS 本地 TTS 适配器（小样本克隆 + 语音合成）"""

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: Optional[str] = "F5TTS",
        device: str = "cpu",
        sample_rate: int = 24000,
    ):
        super().__init__(
            model_path=model_path,
            model_name=model_name or "F5TTS",
            device=device,
            sample_rate=sample_rate,
        )

    def _load_model(self):
        try:
            from f5_tts.api import F5TTS  # type: ignore
        except ImportError as e:
            raise ImportError(
                "F5-TTS 未安装。请先安装 F5-TTS 及其依赖（torch）再使用该后端。"
            ) from e
        model = F5TTS(model_dir=self.model_path)
        self._model_version = getattr(model, "version", "unknown")
        return model

    def _run_inference(
        self, model, text: str, voice_id: str, speed: float, pitch: float, kwargs: Dict[str, Any]
    ) -> Any:
        reference_audio = kwargs.get("reference_audio") or voice_id
        prompt_text = kwargs.get("prompt_text") or ""
        ref_file = reference_audio if reference_audio and reference_audio != "default" else None

        result = model.infer(
            ref_file=ref_file,
            ref_text=prompt_text,
            gen_text=text,
            speed=speed,
        )
        # F5TTS.infer 返回 (audio, sample_rate)
        if isinstance(result, tuple) and len(result) == 2:
            audio, sr = result
        else:
            audio, sr = result, self.sample_rate
        return audio, sr


class VoiceAdapter(VoiceAdapterInterface):
    """
    Factory for creating voice adapters

    Automatically selects QwenTTSAdapter if configured,
    can be extended for other TTS backends.
    """

    def __init__(self, backend: str = "qwen", **kwargs):
        """
        创建指定后端的语音适配器

        Args:
            backend: qwen | cosyvoice | f5-tts
            **kwargs: 透传给具体适配器的参数（base_url/model_path 等）

        Raises:
            ValueError: 不支持的 backend
        """
        self.backend = backend
        normalized = backend.lower().replace("_", "-")
        if normalized == "qwen":
            self._adapter = QwenTTSAdapter(**kwargs)
        elif normalized in ("cosyvoice", "cosy-voice"):
            self._adapter = CosyVoiceAdapter(**kwargs)
        elif normalized in ("f5-tts", "f5tts"):
            self._adapter = F5TTSAdapter(**kwargs)
        else:
            raise ValueError(f"Unsupported voice backend: {backend}")

    def model_info(self) -> Dict[str, Any]:
        """返回当前后端的模型版本/参数信息（进入 Artifact 可复现）"""
        if hasattr(self._adapter, "model_info"):
            return self._adapter.model_info()
        return {
            "backend": self.backend,
            "model_name": self.backend,
            "model_version": None,
        }

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
