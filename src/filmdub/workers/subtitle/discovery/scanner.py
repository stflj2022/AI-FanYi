"""
字幕扫描器 - 发现视频内嵌字幕和外部字幕文件
"""

import logging
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re

from ..config import SubtitleConfig, SubtitleFormat

logger = logging.getLogger(__name__)


@dataclass
class SubtitleTrack:
    """字幕轨道信息"""
    index: int
    codec: str
    language: Optional[str]
    title: Optional[str]
    is_forced: bool = False
    is_default: bool = False


@dataclass
class ExternalSubtitle:
    """外部字幕文件信息"""
    path: Path
    format: SubtitleFormat
    language: Optional[str]
    size: int


class SubtitleScanner:
    """字幕扫描器"""

    # 语言代码映射
    LANGUAGE_MAP = {
        'chi': 'zh-CN',
        'zh': 'zh-CN',
        'zho': 'zh-CN',
        'chinese': 'zh-CN',
        'eng': 'en',
        'en': 'en',
        'english': 'en',
        'jpn': 'ja',
        'ja': 'ja',
        'japanese': 'ja',
        'kor': 'ko',
        'ko': 'ko',
        'korean': 'ko',
        'fre': 'fr',
        'fr': 'fr',
        'french': 'fr',
        'spa': 'es',
        'es': 'es',
        'spanish': 'es',
        'deu': 'de',
        'de': 'de',
        'german': 'de',
    }

    # 字幕扩展名
    SUBTITLE_EXTENSIONS = {
        '.srt': SubtitleFormat.SRT,
        '.ass': SubtitleFormat.ASS,
        '.ssa': SubtitleFormat.SSA,
        '.vtt': SubtitleFormat.VTT,
        '.ttml': SubtitleFormat.TTML,
        '.xml': SubtitleFormat.TTML,
        '.scc': SubtitleFormat.SCC,
    }

    def __init__(self, config: SubtitleConfig):
        """
        初始化扫描器

        Args:
            config: 字幕配置
        """
        self.config = config

    def scan_video_subtitles(self, video_path: Path) -> List[SubtitleTrack]:
        """
        扫描视频内嵌字幕

        Args:
            video_path: 视频文件路径

        Returns:
            字幕轨道列表
        """
        if not video_path.exists():
            logger.error(f"Video file not found: {video_path}")
            return []

        try:
            # 使用 ffprobe 扫描字幕流
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                str(video_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            data = json.loads(result.stdout)
            tracks = []

            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'subtitle':
                    track = self._parse_subtitle_stream(stream)
                    if track:
                        tracks.append(track)
                        logger.info(f"Found subtitle track: index={track.index}, "
                                  f"language={track.language}, codec={track.codec}")

            return tracks

        except subprocess.CalledProcessError as e:
            logger.error(f"ffprobe failed: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ffprobe output: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error scanning video subtitles: {e}")
            return []

    def _parse_subtitle_stream(self, stream: Dict[str, Any]) -> Optional[SubtitleTrack]:
        """解析字幕流"""
        try:
            index = stream.get('index')
            codec = stream.get('codec_name', 'unknown')

            # 解析语言
            tags = stream.get('tags', {})
            language = tags.get('language')
            if language:
                language = self.LANGUAGE_MAP.get(language.lower(), language)

            title = tags.get('title')
            is_forced = tags.get('forced', '0') == '1'
            is_default = tags.get('default', '0') == '1'

            return SubtitleTrack(
                index=index,
                codec=codec,
                language=language,
                title=title,
                is_forced=is_forced,
                is_default=is_default
            )

        except Exception as e:
            logger.warning(f"Failed to parse subtitle stream: {e}")
            return None

    def scan_external_subtitles(
        self,
        video_path: Path,
        search_paths: Optional[List[Path]] = None
    ) -> List[ExternalSubtitle]:
        """
        扫描外部字幕文件

        Args:
            video_path: 视频文件路径
            search_paths: 搜索路径列表（默认使用配置的路径）

        Returns:
            外部字幕文件列表
        """
        if search_paths is None:
            search_paths = self.config.get_subtitle_search_paths(str(video_path.parent))

        subtitles = []
        video_stem = video_path.stem

        for search_path in search_paths:
            path = Path(search_path)
            if not path.exists():
                continue

            # 扫描字幕文件
            for ext, fmt in self.SUBTITLE_EXTENSIONS.items():
                for file_path in path.glob(f"{video_stem}*{ext}"):
                    language = self._guess_language_from_filename(file_path.name)
                    subtitles.append(ExternalSubtitle(
                        path=file_path,
                        format=fmt,
                        language=language,
                        size=file_path.stat().st_size
                    ))
                    logger.info(f"Found external subtitle: {file_path}, "
                              f"format={fmt}, language={language}")

        return subtitles

    def _guess_language_from_filename(self, filename: str) -> Optional[str]:
        """
        从文件名猜测语言

        Args:
            filename: 文件名

        Returns:
            语言代码
        """
        filename_lower = filename.lower()

        # 检查常见语言标记
        for lang_code, lang_name in self.LANGUAGE_MAP.items():
            if lang_code in filename_lower:
                return lang_name

        # 检查中文字符
        if re.search(r'[\u4e00-\u9fff]', filename):
            return 'zh-CN'

        return None

    def extract_embedded_subtitle(
        self,
        video_path: Path,
        track_index: int,
        output_path: Path
    ) -> bool:
        """
        提取内嵌字幕

        Args:
            video_path: 视频文件路径
            track_index: 字幕轨道索引
            output_path: 输出文件路径

        Returns:
            是否成功
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-map', f'0:s:{track_index}',
                '-c:s', 'srt',  # 转换为 SRT 格式
                '-y',  # 覆盖输出文件
                str(output_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.info(f"Extracted subtitle track {track_index} to {output_path}")
                return True
            else:
                logger.error(f"Failed to extract subtitle: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error extracting subtitle: {e}")
            return False

    def get_subtitle_summary(
        self,
        video_path: Path
    ) -> Dict[str, Any]:
        """
        获取字幕摘要信息

        Args:
            video_path: 视频文件路径

        Returns:
            字幕摘要
        """
        embedded = self.scan_video_subtitles(video_path)
        external = self.scan_external_subtitles(video_path)

        # 统计语言
        embedded_languages = [t.language for t in embedded if t.language]
        external_languages = [s.language for s in external if s.language]

        return {
            "video_path": str(video_path),
            "embedded_subtitles": {
                "count": len(embedded),
                "languages": embedded_languages,
                "tracks": [
                    {
                        "index": t.index,
                        "language": t.language,
                        "codec": t.codec,
                        "is_default": t.is_default,
                        "is_forced": t.is_forced
                    }
                    for t in embedded
                ]
            },
            "external_subtitles": {
                "count": len(external),
                "languages": external_languages,
                "files": [
                    {
                        "path": str(s.path),
                        "format": s.format.value,
                        "language": s.language,
                        "size": s.size
                    }
                    for s in external
                ]
            },
            "has_chinese_subtitle": (
                'zh-CN' in embedded_languages or 'zh-CN' in external_languages
            ),
            "has_english_subtitle": (
                'en' in embedded_languages or 'en' in external_languages
            )
        }
