"""
TTS 模型管理器

管理 TTS 后端的创建、切换和统一合成。
自 ticket-035 起支持通过 Adapter 接口统一走 qwen/cosyvoice/f5-tts 后端。
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

from .config import M09Config


class TTSModelManager:
    """TTS 模型管理器"""

    def __init__(self, config: M09Config = None):
        """
        初始化模型管理器

        Args:
            config: M09 配置
        """
        self.config = config or M09Config()
        self.models = {}
        self.current_model = None

        # 检查 CUDA 可用性（torch 未安装时默认为 CPU）
        self.device = self._resolve_device()

        logger.info(f"Using device: {self.device}")

    def _resolve_device(self) -> str:
        """解析运行设备，torch 不可用时回退到 CPU。"""
        try:
            import torch
            if torch.cuda.is_available() and self.config.cosyvoice_device == "cuda":
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    def load_model(self, model_name: str = None) -> bool:
        """
        加载模型

        Args:
            model_name: 模型名称

        Returns:
            是否成功
        """
        from filmdub.adapter.voice import normalize_voice_backend

        model_name = normalize_voice_backend(model_name or self.config.default_model)

        if model_name in self.models:
            logger.info(f"Model {model_name} already loaded")
            self.current_model = self.models[model_name]
            return True

        try:
            logger.info(f"Loading model: {model_name}")

            if model_name == "cosyvoice":
                model = self._load_cosyvoice()
            elif model_name == normalize_voice_backend("f5_tts") and self.config.enable_f5_tts:
                model = self._load_f5_tts()
            else:
                logger.error(f"Unknown or disabled model: {model_name}")
                return False

            self.models[model_name] = model
            self.current_model = model

            logger.info(f"Model {model_name} loaded successfully")

            return True

        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return False

    def _load_cosyvoice(self) -> Any:
        """加载 CosyVoice 模型（复用 CosyVoiceAdapter.load_model，避免重复导入/文案）"""
        from filmdub.adapter import CosyVoiceAdapter

        adapter = CosyVoiceAdapter(
            model_path=self.config.model_path,
            model_name=self.config.cosyvoice_model_name,
            device=self.config.cosyvoice_device,
        )
        return adapter.load_model()

    def _load_f5_tts(self) -> Any:
        """加载 F5-TTS 模型（复用 F5TTSAdapter.load_model）"""
        from filmdub.adapter import F5TTSAdapter

        adapter = F5TTSAdapter(
            model_path=self.config.f5_tts_model_path,
            sample_rate=self.config.sample_rate,
        )
        return adapter.load_model()

    def switch_model(self, model_name: str) -> bool:
        """
        切换模型

        Args:
            model_name: 模型名称

        Returns:
            是否成功
        """
        from filmdub.adapter.voice import normalize_voice_backend

        model_name = normalize_voice_backend(model_name)
        if model_name not in self.models:
            logger.info(f"Model {model_name} not loaded, loading now...")
            return self.load_model(model_name)

        self.current_model = self.models[model_name]
        logger.info(f"Switched to model: {model_name}")

        return True

    def unload_model(self, model_name: str) -> bool:
        """
        卸载模型

        Args:
            model_name: 模型名称

        Returns:
            是否成功
        """
        from filmdub.adapter.voice import normalize_voice_backend

        model_name = normalize_voice_backend(model_name)
        if model_name not in self.models:
            logger.warning(f"Model {model_name} not loaded")
            return False

        # 先记录是否为当前模型（删除后无法再查询名称映射）
        was_current = self.get_current_model_name() == model_name

        del self.models[model_name]

        if was_current:
            # 找到另一个模型作为当前模型
            if self.models:
                self.current_model = next(iter(self.models.values()))
            else:
                self.current_model = None

        logger.info(f"Model {model_name} unloaded")

        return True

    def get_current_model_name(self) -> Optional[str]:
        """获取当前模型名称"""
        for name, model in self.models.items():
            if model is self.current_model:
                return name
        return None

    def get_model_info(self, model_name: str = None) -> Optional[Dict[str, Any]]:
        """
        获取模型信息

        Args:
            model_name: 模型名称

        Returns:
            模型信息
        """
        from filmdub.adapter.voice import normalize_voice_backend

        model_name = model_name or self.get_current_model_name()
        if model_name is not None:
            model_name = normalize_voice_backend(model_name)

        if not model_name or model_name not in self.models:
            return None

        model = self.models[model_name]

        return {
            "name": model_name,
            "model_type": model.__class__.__name__,
            "device": str(self.device),
            "is_loaded": True
        }

    def get_available_models(self) -> List[str]:
        """获取可用模型列表（业务层命名：cosyvoice/f5_tts/qwen，与 Adapter 层 f5-tts 归一名区分）"""
        models = ["cosyvoice"]

        if self.config.enable_f5_tts:
            models.append("f5_tts")

        return models

    # ------------------------------------------------------------------
    # Adapter 统一入口（ticket-035）
    # ------------------------------------------------------------------
    def create_adapter(self, backend: Optional[str] = None, **kwargs) -> Any:
        """
        根据 backend 创建统一 VoiceAdapter

        Args:
            backend: 业务模型名（cosyvoice/f5_tts/qwen），默认取 config.default_model
            **kwargs: 透传给 Adapter 的参数

        Returns:
            VoiceAdapter 实例（qwen/cosyvoice/f5-tts）

        Raises:
            ValueError: 不支持的 backend
        """
        from filmdub.adapter import VoiceAdapter
        from filmdub.adapter.voice import normalize_voice_backend

        backend = backend or self.config.default_model
        adapter_backend = normalize_voice_backend(backend)
        adapter_kwargs = dict(kwargs)

        if adapter_backend == "cosyvoice":
            adapter_kwargs.setdefault("model_path", self.config.model_path)
            adapter_kwargs.setdefault("model_name", self.config.cosyvoice_model_name)
            adapter_kwargs.setdefault("device", self.config.cosyvoice_device)
            adapter_kwargs.setdefault("sample_rate", self.config.sample_rate)
        elif adapter_backend == "f5-tts":
            adapter_kwargs.setdefault("model_path", self.config.f5_tts_model_path)
            adapter_kwargs.setdefault("sample_rate", self.config.sample_rate)
        elif adapter_backend == "qwen":
            adapter_kwargs.setdefault("use_openai_api", True)

        return VoiceAdapter(backend=adapter_backend, **adapter_kwargs)

    async def synthesize_via_adapter(
        self,
        text: str,
        voice_id: str,
        output_path: str | Path,
        speed: float = 1.0,
        pitch: float = 1.0,
        backend: Optional[str] = None,
        **kwargs
    ) -> tuple[Path, Dict[str, Any]]:
        """
        通过 Adapter 统一合成语音（后端可配置切换，无需改业务代码）

        Args:
            text: 合成文本
            voice_id: 音色 ID
            output_path: 输出路径
            speed: 语速因子
            pitch: 音高因子
            backend: 后端（默认 config.default_model）
            **kwargs: 透传给 Adapter 的额外参数

        Returns:
            (输出音频路径, 模型信息 dict)
        """
        from pathlib import Path

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        adapter = self.create_adapter(backend=backend)
        try:
            result = await adapter.synthesize(
                text=text,
                voice_id=voice_id,
                output_path=output_path,
                speed=speed,
                pitch=pitch,
                **kwargs,
            )
            model_info = adapter.model_info()
            logger.info(f"Adapter synthesis complete (backend={backend or self.config.default_model}): {result}")
            return Path(result), model_info
        finally:
            await adapter.close()
