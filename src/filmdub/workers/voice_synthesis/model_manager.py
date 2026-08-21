"""
TTS 模型管理器

管理 TTS 模型的加载、切换和卸载
"""
from typing import Optional, Dict, Any, List
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
        model_name = model_name or self.config.default_model

        if model_name in self.models:
            logger.info(f"Model {model_name} already loaded")
            self.current_model = self.models[model_name]
            return True

        try:
            logger.info(f"Loading model: {model_name}")

            if model_name == "cosyvoice":
                model = self._load_cosyvoice()
            elif model_name == "f5_tts" and self.config.enable_f5_tts:
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
        """加载 CosyVoice 模型。

        需要安装 CosyVoice 及其依赖（torch 等），否则抛出 ImportError。
        """
        try:
            from cosyvoice.cli.cosyvoice import CosyVoice  # type: ignore

            logger.info("Loading CosyVoice model...")
            model = CosyVoice(self.config.cosyvoice_model_name)
            logger.info("CosyVoice model loaded")
            return model

        except ImportError as e:
            raise ImportError(
                "CosyVoice is not installed. Please install CosyVoice and its "
                "dependencies (torch) before using voice synthesis."
            ) from e

    def _load_f5_tts(self) -> Any:
        """加载 F5-TTS 模型。

        需要安装 F5-TTS 及其依赖，否则抛出 ImportError。
        """
        try:
            from f5_tts.api import F5TTS  # type: ignore

            logger.info("Loading F5-TTS model...")
            model = F5TTS(model_dir=self.config.f5_tts_model_path)
            logger.info("F5-TTS model loaded")
            return model

        except ImportError as e:
            raise ImportError(
                "F5-TTS is not installed. Please install F5-TTS and its "
                "dependencies before using voice synthesis."
            ) from e

    def switch_model(self, model_name: str) -> bool:
        """
        切换模型

        Args:
            model_name: 模型名称

        Returns:
            是否成功
        """
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
        if model_name not in self.models:
            logger.warning(f"Model {model_name} not loaded")
            return False

        del self.models[model_name]

        if self.current_model is not None and model_name == self.get_current_model_name():
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
        model_name = model_name or self.get_current_model_name()

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
        """获取可用模型列表"""
        models = ["cosyvoice"]

        if self.config.enable_f5_tts:
            models.append("f5_tts")

        return models
