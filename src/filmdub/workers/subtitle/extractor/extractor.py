"""
对白提取器 - 从字幕中提取对白并分类
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from ..importer.parser import SubtitleEntry
from ..importer.normalizer import DialogueNormalizer
from ...subtitle.config import SubtitleConfig, DialogueType

logger = logging.getLogger(__name__)


@dataclass
class DialogueItem:
    """对白条目"""
    id: str
    start: float
    end: float
    text: str
    normalized_text: str
    dialogue_type: DialogueType
    speaker_hint: Optional[str] = None
    emotion_hint: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DialogueExtractor:
    """对白提取器"""

    def __init__(self, config: SubtitleConfig):
        """
        初始化提取器

        Args:
            config: 字幕配置
        """
        self.config = config
        self.normalizer = DialogueNormalizer()

        # 编译对话模式
        self.patterns = {
            'music': re.compile(config.dialogue_patterns['music'], re.IGNORECASE),
            'sfx': re.compile(config.dialogue_patterns['sfx'], re.IGNORECASE),
            'description': re.compile(config.dialogue_patterns['description'], re.IGNORECASE),
        }

    def extract(self, entries: List[SubtitleEntry]) -> List[DialogueItem]:
        """
        从字幕中提取对白

        Args:
            entries: 字幕条目列表

        Returns:
            对白条目列表
        """
        dialogues = []

        for entry in entries:
            item = self._extract_dialogue(entry)
            if item:
                dialogues.append(item)

        logger.info(f"Extracted {len(dialogues)} dialogue items from {len(entries)} subtitle entries")

        # 统计类型
        type_counts = {}
        for d in dialogues:
            t = d.dialogue_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        logger.debug(f"Dialogue type distribution: {type_counts}")

        return dialogues

    def _extract_dialogue(self, entry: SubtitleEntry) -> Optional[DialogueItem]:
        """从单个字幕条目提取对白"""
        text = entry.text

        # 1. 分类对话类型
        dialogue_type = self._classify_dialogue_type(text)

        # 2. 提取情感提示
        text, emotion_hint = self.normalizer.extract_emotion_hint(text)

        # 3. 提取说话人提示
        text, speaker_hint = self.normalizer.extract_speaker_hint(text)

        # 4. 标准化文本
        normalization_result = self.normalizer.normalize(text)

        # 5. 检查是否应该保留
        if dialogue_type == DialogueType.UNKNOWN and not normalization_result.normalized_text.strip():
            return None

        # 6. 创建对白条目
        item = DialogueItem(
            id=f"dlg_{entry.index:06d}",
            start=entry.start,
            end=entry.end,
            text=text,
            normalized_text=normalization_result.normalized_text,
            dialogue_type=dialogue_type,
            speaker_hint=speaker_hint,
            emotion_hint=emotion_hint,
            metadata={
                'original_text': entry.text,
                'normalization': normalization_result.metadata,
                'entry_index': entry.index
            }
        )

        return item

    def _classify_dialogue_type(self, text: str) -> DialogueType:
        """
        分类对话类型

        Args:
            text: 文本

        Returns:
            对话类型
        """
        text_lower = text.lower().strip()

        # 检查是否为音乐
        if any(pattern.search(text_lower) for pattern in self.patterns.values()):
            return DialogueType.MUSIC

        # 检查是否为描述性文本（方括号、尖括号）
        if re.match(r'^[\[\(].*?[\]\)]$', text.strip()):
            # 进一步判断是否为音效描述
            sfx_keywords = ['door', 'phone', 'footsteps', 'car', 'gun', 'explosion',
                           'laughter', 'applause', 'cough', 'sneeze']
            if any(keyword in text_lower for keyword in sfx_keywords):
                return DialogueType.SFX
            else:
                return DialogueType.DESCRIPTION

        # 检查是否只包含符号
        if not re.search(r'[a-zA-Z\u4e00-\u9fff0-9]', text):
            return DialogueType.UNKNOWN

        # 默认为对白
        return DialogueType.DIALOGUE

    def filter_dialogues(
        self,
        dialogues: List[DialogueItem],
        include_types: Optional[List[DialogueType]] = None
    ) -> List[DialogueItem]:
        """
        过滤对话类型

        Args:
            dialogues: 对话条目列表
            include_types: 包含的类型列表（None表示全部）

        Returns:
            过滤后的对话列表
        """
        if include_types is None:
            return dialogues

        return [d for d in dialogues if d.dialogue_type in include_types]

    def get_statistics(self, dialogues: List[DialogueItem]) -> Dict[str, Any]:
        """
        获取对话统计信息

        Args:
            dialogues: 对话条目列表

        Returns:
            统计信息
        """
        # 按类型统计
        type_counts = {}
        for d in dialogues:
            t = d.dialogue_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        # 说话人统计
        speaker_counts = {}
        for d in dialogues:
            if d.speaker_hint:
                speaker_counts[d.speaker_hint] = speaker_counts.get(d.speaker_hint, 0) + 1

        # 情感统计
        emotion_counts = {}
        for d in dialogues:
            if d.emotion_hint:
                emotion_counts[d.emotion_hint] = emotion_counts.get(d.emotion_hint, 0) + 1

        # 时长统计
        durations = [d.end - d.start for d in dialogues]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total_dialogues": len(dialogues),
            "type_distribution": type_counts,
            "speaker_hints": speaker_counts,
            "emotion_hints": emotion_counts,
            "avg_duration": avg_duration,
            "total_duration": sum(durations)
        }
