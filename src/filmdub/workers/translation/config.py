"""Translation module configuration."""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class TranslationConfig(BaseSettings):
    """Translation module configuration."""

    # 翻译引擎类型
    engine: str = "qwen"

    # Qwen 模型配置
    qwen_model_path: str = ""
    qwen_api_url: str = "http://localhost:8000/v1/chat/completions"
    qwen_api_key: str = ""
    qwen_temperature: float = 0.7
    qwen_max_tokens: int = 2000

    # 翻译记忆库配置
    translation_memory_path: str = "data/translation_memory.json"
    enable_translation_memory: bool = True
    similarity_threshold: float = 0.85

    # 批量翻译配置
    batch_size: int = 10
    batch_timeout: int = 30

    # 术语库配置
    glossary_path: str = "data/glossary.json"

    model_config = ConfigDict(
        env_prefix="TRANSLATION_",
        env_file=".env",
        extra="ignore"
    )


def get_config() -> TranslationConfig:
    """Get translation configuration."""
    return TranslationConfig()
