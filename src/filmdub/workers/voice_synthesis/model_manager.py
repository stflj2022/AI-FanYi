"""
TTS 模型管理器

管理 TTS 模型的加载、切换和卸载
"""
from typing import Optional, Dict, Any
from loguru import logger
import torch

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

        # 检查 CUDA 可用性
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() and self.config.cosyvoice_device == "cuda"
            else "cpu"
        )

        logger.info(f"Using device: {self.device}")

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
                logger.error(f"Unknown model: {model_name}")
                return False

            self.models[model_name] = model
            self.current_model = model

            logger.info(f"Model {model_name} loaded successfully")

            return True

        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return False

    def _load_cosyvoice(self) -> Any:
        """加载 CosyVoice 模型"""
        try:
            # TODO: 实际加载 CosyVoice
            # 这里只是框架
            logger.info("Loading CosyVoice model...")

            # 框架代码
            class MockCosyVoice:
                def __init__(self):
                    self.model_name = "CosyVoice-300M"

                def inference(self, text, **kwargs):
                    # 返回模拟音频
                    import numpy as np
                    return np.random.rand(24000).astype(np.float32)

            model = MockCosyVoice()

            logger.info("CosyVoice model loaded")

            return model

        except Exception as e:
            logger.error(f"Failed to load CosyVoice: {e}")
            raise

    def _load_f5_tts(self) -> Any:
        """加载 F5-TTS 模型"""
        try:
            # TODO: 实际加载 F5-TTS
            # 这里只是框架
            logger.info("Loading F5-TTS model...")

            # 框架代码
            class MockF5TTS:
                def __init__(self):
                    self.model_name = "F5-TTS"

                def inference(self, text, **kwargs):
                    # 返回模拟音频
                    import numpy as np
                    return np.random.rand(24000).astype(np.float32)

            model = MockF5TTS()

            logger.info("F5-TTS model loaded")

            return model

        except Exception as e:
            logger.error(f"Failed to load F5-TTS: {e}")
            raise

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

        if self.current_model and model_name == self.get_current_model_name():
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
            if model == self.current_model:
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
