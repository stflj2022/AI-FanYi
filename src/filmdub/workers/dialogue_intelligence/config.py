"""
M07 Dialogue Intelligence 配置
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class M07Config:
    """M07 配置"""

    # LLM 配置
    llm_endpoint: str = "http://localhost:8000"
    llm_model: str = "qwen"
    llm_temperature: float = 0.7

    # 对白处理
    enable_terminology_check: bool = True
    enable_culture_localization: bool = True
    enable_tone_adjustment: bool = True

    # 术语库路径
    terminology_db_path: Optional[str] = None

    # 性能
    batch_size: int = 16
    max_concurrent_jobs: int = 4
