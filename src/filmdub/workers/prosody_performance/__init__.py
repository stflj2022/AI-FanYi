"""
M10 Prosody & Performance Worker

音色、韵律和表演处理模块

"M09 解决谁在说，M10 解决像不像人在说"
"""

from .m10_worker import M10Worker
from .config import M10Config
from .processor import ProsodyProcessor
from .models import EmotionType, ProsodyParams

__all__ = [
    "M10Worker",
    "M10Config",
    "ProsodyProcessor",
    "EmotionType",
    "ProsodyParams",
]
