"""
Module 03 配置系统
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class TranslationMode(str, Enum):
    """翻译模式"""
    AUTO = "auto"  # 自动选择
    EXISTING_CHINESE = "existing_chinese"  # 使用现成中文字幕
    QWEN_TRANSLATION = "qwen_translation"  # 使用Qwen翻译
    ASR = "asr"  # 使用ASR


class SubtitleFormat(str, Enum):
    """字幕格式"""
    SRT = "srt"
    ASS = "ass"
    SSA = "ssa"
    VTT = "vtt"
    TTML = "ttml"
    SCC = "scc"
    WEBVTT = "webvtt"


class DialogueType(str, Enum):
    """对白类型"""
    DIALOGUE = "dialogue"  # 对白
    MUSIC = "music"  # 音乐
    SFX = "sfx"  # 音效
    DESCRIPTION = "description"  # 描述
    UNKNOWN = "unknown"  # 未知


@dataclass
class SubtitleConfig:
    """字幕处理配置"""

    # 翻译设置
    translation_mode: TranslationMode = TranslationMode.AUTO
    target_language: str = "zh-CN"

    # 字幕搜索路径
    subtitle_search_paths: List[str] = field(default_factory=list)

    # 字幕匹配权重
    filename_weight: float = 0.30
    title_weight: float = 0.20
    season_episode_weight: float = 0.20
    language_weight: float = 0.15
    duration_weight: float = 0.15

    # 字幕匹配阈值
    subtitle_match_threshold: float = 0.70

    # 字幕质量评分阈值
    min_subtitle_quality: float = 0.80

    # 字幕验证
    max_subtitle_duration: float = 45.0  # 单条字幕最大时长（秒）
    min_subtitle_duration: float = 0.5   # 单条字幕最小时长（秒）
    max_subtitle_gap: float = 10.0       # 字幕间最大间隔（秒）

    # 时间轴对齐
    max_duration_diff: float = 5.0       # 字幕与视频最大时长差异（秒）
    max_offset_search: float = 60.0      # 最大offset搜索范围（秒）

    # 对白提取
    dialogue_patterns: Dict[str, str] = field(default_factory=lambda: {
        "music": r"♪|♫|\[music\]|\(music\)|<music>",
        "sfx": r"\[.*?\]|<.*?>|\(.*?\)",
        "description": r"\[.*?\]|<.*?>|\(.*?\)",
    })

    # 翻译设置
    translation_context_size: int = 5  # 上下文大小（前N句+后N句）
    min_translation_confidence: float = 0.85

    # ASR设置
    asr_model: str = "large-v3"  # Whisper模型
    asr_language: str = "en"     # ASR语言

    # 批处理
    batch_size: int = 100  # 批处理大小

    # 缓存
    enable_cache: bool = True
    cache_ttl: int = 86400  # 缓存过期时间（秒）

    def __post_init__(self):
        """初始化后处理"""
        if not self.subtitle_search_paths:
            self.subtitle_search_paths = [
                ".",  # 当前目录
                "subtitles",  # subtitles子目录
                "subs",  # subs子目录
            ]

    def get_subtitle_search_paths(self, media_dir: str) -> List[str]:
        """获取字幕搜索路径"""
        import os
        paths = []
        for p in self.subtitle_search_paths:
            if os.path.isabs(p):
                paths.append(p)
            else:
                paths.append(os.path.join(media_dir, p))
        return paths
