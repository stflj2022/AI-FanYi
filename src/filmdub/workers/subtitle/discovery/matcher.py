"""
字幕匹配器 - 根据文件名、作品名、季集等匹配字幕
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

from ..config import SubtitleConfig
from .scanner import ExternalSubtitle

logger = logging.getLogger(__name__)


@dataclass
class SubtitleMatch:
    """字幕匹配结果"""
    subtitle: ExternalSubtitle
    score: float
    details: Dict[str, Any]


class SubtitleMatcher:
    """字幕匹配器"""

    def __init__(self, config: SubtitleConfig):
        """
        初始化匹配器

        Args:
            config: 字幕配置
        """
        self.config = config

    def match_subtitle_to_video(
        self,
        subtitle: ExternalSubtitle,
        video_path: Path,
        video_duration: float,
        episode_info: Optional[Dict[str, Any]] = None
    ) -> SubtitleMatch:
        """
        匹配字幕到视频

        Args:
            subtitle: 外部字幕
            video_path: 视频文件路径
            video_duration: 视频时长（秒）
            episode_info: 剧集信息（包含 title, season, episode 等）

        Returns:
            匹配结果
        """
        scores = {}
        details = {}

        # 1. 文件名匹配 (30%)
        filename_score = self._score_filename(subtitle.path.name, video_path.name)
        scores['filename'] = filename_score
        details['filename'] = {
            'video_name': video_path.name,
            'subtitle_name': subtitle.path.name,
            'score': filename_score
        }

        # 2. 作品名匹配 (20%)
        title_score = 0.0
        if episode_info:
            title = episode_info.get('title', '')
            if title:
                title_score = self._score_title(subtitle.path.name, title)
        scores['title'] = title_score
        details['title'] = {
            'episode_title': episode_info.get('title') if episode_info else None,
            'score': title_score
        }

        # 3. 季集匹配 (20%)
        season_episode_score = 0.0
        if episode_info:
            season = episode_info.get('season')
            episode = episode_info.get('episode')
            if season is not None or episode is not None:
                season_episode_score = self._score_season_episode(
                    subtitle.path.name, season, episode
                )
        scores['season_episode'] = season_episode_score
        details['season_episode'] = {
            'season': episode_info.get('season') if episode_info else None,
            'episode': episode_info.get('episode') if episode_info else None,
            'score': season_episode_score
        }

        # 4. 语言匹配 (15%)
        language_score = self._score_language(subtitle.language)
        scores['language'] = language_score
        details['language'] = {
            'subtitle_language': subtitle.language,
            'score': language_score
        }

        # 5. 时长匹配 (15%)
        duration_score = 0.0
        subtitle_duration = self._estimate_subtitle_duration(subtitle.path)
        if subtitle_duration and video_duration > 0:
            duration_score = self._score_duration(subtitle_duration, video_duration)
        scores['duration'] = duration_score
        details['duration'] = {
            'video_duration': video_duration,
            'subtitle_duration': subtitle_duration,
            'score': duration_score
        }

        # 计算总评分
        total_score = (
            scores['filename'] * self.config.filename_weight +
            scores['title'] * self.config.title_weight +
            scores['season_episode'] * self.config.season_episode_weight +
            scores['language'] * self.config.language_weight +
            scores['duration'] * self.config.duration_weight
        )

        logger.debug(f"Subtitle match: {subtitle.path.name}, score={total_score:.2f}, "
                    f"details={details}")

        return SubtitleMatch(
            subtitle=subtitle,
            score=total_score,
            details=details
        )

    def _score_filename(self, subtitle_name: str, video_name: str) -> float:
        """文件名相似度评分"""
        # 提取基础名称（去除扩展名和语言标记）
        sub_base = self._extract_base_name(subtitle_name)
        vid_base = self._extract_base_name(video_name)

        # 计算相似度
        similarity = SequenceMatcher(None, sub_base, vid_base).ratio()

        # 如果基础名称完全相同，给予更高分数
        if sub_base.lower() == vid_base.lower():
            similarity = 1.0

        return similarity

    def _extract_base_name(self, filename: str) -> str:
        """提取文件基础名称（去除扩展名和语言标记）"""
        # 去除扩展名
        name = Path(filename).stem

        # 去除常见的语言标记
        patterns = [
            r'\.?\b(chi|zh|zho|chinese|eng|en|english|jpn|ja|japanese)\b\.?',
            r'\.?\b(srt|ass|ssa|vtt|sub)\b',
            r'[\[\(].*?[\]\)]',  # 去除方括号和圆括号内容
        ]

        for pattern in patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)

        return name.strip()

    def _score_title(self, subtitle_name: str, title: str) -> float:
        """作品名匹配评分"""
        # 将作品名转换为文件名格式
        title_normalized = title.lower().replace(' ', '.').replace('-', '.')
        subtitle_lower = subtitle_name.lower()

        # 检查标题是否在文件名中
        if title_normalized in subtitle_lower:
            return 1.0

        # 检查部分匹配
        title_parts = title_normalized.split('.')
        matched_parts = sum(1 for part in title_parts if part in subtitle_lower)
        return matched_parts / len(title_parts) if title_parts else 0.0

    def _score_season_episode(
        self,
        subtitle_name: str,
        season: Optional[int],
        episode: Optional[int]
    ) -> float:
        """季集匹配评分"""
        if season is None and episode is None:
            return 0.0

        subtitle_lower = subtitle_name.lower()
        score = 0.0
        max_score = 0.0

        # 匹配季
        if season is not None:
            max_score += 1.0
            season_patterns = [
                rf's0*{season}',
                rf'season\s*0*{season}',
            ]
            for pattern in season_patterns:
                if re.search(pattern, subtitle_lower):
                    score += 1.0
                    break

        # 匹配集
        if episode is not None:
            max_score += 1.0
            episode_patterns = [
                rf'e0*{episode}',
                rf'ep0*{episode}',
                rf'episode\s*0*{episode}',
            ]
            for pattern in episode_patterns:
                if re.search(pattern, subtitle_lower):
                    score += 1.0
                    break

        # 匹配 SxxExx 格式
        if season is not None and episode is not None:
            max_score += 1.0
            se_pattern = rf's0*{season}\s*[.-_]?\s*e0*{episode}'
            if re.search(se_pattern, subtitle_lower):
                score += 1.0

        return score / max_score if max_score > 0 else 0.0

    def _score_language(self, language: Optional[str]) -> float:
        """语言匹配评分"""
        if not language:
            return 0.0

        # 目标语言评分
        target_language = self.config.target_language

        if language == target_language:
            return 1.0
        elif language.startswith(target_language.split('-')[0]):
            return 0.8
        else:
            return 0.0

    def _estimate_subtitle_duration(self, subtitle_path: Path) -> Optional[float]:
        """估算字幕时长"""
        try:
            # 读取字幕文件
            with open(subtitle_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 如果是 SRT 格式，解析最后一条字幕的结束时间
            if subtitle_path.suffix.lower() == '.srt':
                # 查找所有时间戳
                time_pattern = r'(\d{2}:\d{2}:\d{2},\d{3})'
                timestamps = re.findall(time_pattern, content)

                if len(timestamps) >= 2:
                    # 获取最后一条字幕的结束时间
                    last_end = timestamps[-1]
                    hours, minutes, seconds_ms = last_end.split(':')
                    seconds, milliseconds = seconds_ms.split(',')

                    total_seconds = (
                        int(hours) * 3600 +
                        int(minutes) * 60 +
                        int(seconds) +
                        int(milliseconds) / 1000
                    )
                    return total_seconds

            return None

        except Exception as e:
            logger.warning(f"Failed to estimate subtitle duration: {e}")
            return None

    def _score_duration(self, subtitle_duration: float, video_duration: float) -> float:
        """时长匹配评分"""
        if video_duration == 0:
            return 0.0

        diff = abs(subtitle_duration - video_duration)
        relative_diff = diff / video_duration

        # 差异越小，分数越高
        if relative_diff < 0.01:  # 差异小于1%
            return 1.0
        elif relative_diff < 0.05:  # 差异小于5%
            return 0.9
        elif relative_diff < 0.10:  # 差异小于10%
            return 0.7
        elif relative_diff < 0.20:  # 差异小于20%
            return 0.5
        else:
            return 0.0

    def find_best_subtitle(
        self,
        subtitles: List[ExternalSubtitle],
        video_path: Path,
        video_duration: float,
        episode_info: Optional[Dict[str, Any]] = None
    ) -> Optional[SubtitleMatch]:
        """
        找到最佳匹配的字幕

        Args:
            subtitles: 字幕列表
            video_path: 视频文件路径
            video_duration: 视频时长
            episode_info: 剧集信息

        Returns:
            最佳匹配结果
        """
        if not subtitles:
            return None

        matches = []
        for subtitle in subtitles:
            match = self.match_subtitle_to_video(
                subtitle, video_path, video_duration, episode_info
            )
            matches.append(match)

        # 按评分排序
        matches.sort(key=lambda m: m.score, reverse=True)

        # 返回评分最高的（如果超过阈值）
        best = matches[0]
        if best.score >= self.config.subtitle_match_threshold:
            logger.info(f"Best subtitle match: {best.subtitle.path.name}, "
                       f"score={best.score:.2f}")
            return best
        else:
            logger.warning(f"No subtitle meets threshold (best={best.score:.2f})")
            return None
