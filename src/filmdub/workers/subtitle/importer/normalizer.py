"""
对话标准化器 - 清理和标准化对话文本
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NormalizationResult:
    """标准化结果"""
    normalized_text: str
    metadata: Dict[str, Any]


class DialogueNormalizer:
    """对话标准化器"""

    # 引号替换
    QUOTE_REPLACEMENTS = {
        '\u201c': '"',  # 左双引号
        '\u201d': '"',  # 右双引号
        '\u2018': "'",  # 左单引号
        '\u2019': "'",  # 右单引号
        '\u2014': '-',  # 破折号
        '\u2013': '-',  # 短破折号
    }

    # HTML 实体
    HTML_ENTITIES = {
        '&nbsp;': ' ',
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
        '&quot;': '"',
        '&apos;': "'",
    }

    def __init__(self):
        """初始化标准化器"""
        pass

    def normalize(self, text: str) -> NormalizationResult:
        """
        标准化文本

        Args:
            text: 原始文本

        Returns:
            标准化结果
        """
        metadata = {}
        original_text = text

        # 1. 移除 HTML 标签
        text = self._remove_html_tags(text)
        if text != original_text:
            metadata['had_html'] = True

        # 2. 解码 HTML 实体
        text = self._decode_html_entities(text)

        # 3. 标准化引号
        text = self._normalize_quotes(text)

        # 4. 标准化破折号
        text = self._normalize_dashes(text)

        # 5. 标准化空白
        text, whitespace_info = self._normalize_whitespace(text)
        if whitespace_info:
            metadata['whitespace'] = whitespace_info

        # 6. 修复标点符号
        text, punctuation_info = self._normalize_punctuation(text)
        if punctuation_info:
            metadata['punctuation'] = punctuation_info

        # 7. 移除特殊字符（但保留必要的标点）
        text, special_info = self._remove_special_chars(text)
        if special_info:
            metadata['special_chars_removed'] = special_info

        return NormalizationResult(
            normalized_text=text.strip(),
            metadata=metadata
        )

    def _remove_html_tags(self, text: str) -> str:
        """移除 HTML 标签"""
        return re.sub(r'<[^>]+>', '', text)

    def _decode_html_entities(self, text: str) -> str:
        """解码 HTML 实体"""
        for entity, replacement in self.HTML_ENTITIES.items():
            text = text.replace(entity, replacement)
        return text

    def _normalize_quotes(self, text: str) -> str:
        """标准化引号"""
        for quote, replacement in self.QUOTE_REPLACEMENTS.items():
            text = text.replace(quote, replacement)
        return text

    def _normalize_dashes(self, text: str) -> str:
        """标准化破折号"""
        text = re.sub(r'\s*[-–—]\s*', ' - ', text)
        return text

    def _normalize_whitespace(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """标准化空白"""
        info = {}

        # 检测换行符
        if '\n' in text or '\r' in text:
            info['had_linebreaks'] = True

        # 统一空白字符
        text = re.sub(r'[\r\n\t]+', ' ', text)
        text = re.sub(r' +', ' ', text)

        # 移除首尾空白
        original = text
        text = text.strip()

        if len(text) != len(original):
            info['trimmed'] = len(original) - len(text)

        return text, info

    def _normalize_punctuation(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """标准化标点符号"""
        info = {}

        # 确保句子后有正确的标点
        original = text

        # 如果句子以字母结尾，添加句号
        if text and text[-1].isalpha():
            text += '.'
            info['added_period'] = True

        # 确保标点后有空格（除非是句末）
        text = re.sub(r'([.!?;:](?!\s|$))', r'\1 ', text)

        # 移除标点前的空格
        text = re.sub(r'\s+([.!?;,])', r'\1', text)

        if text != original:
            info['punctuation_fixed'] = True

        return text, info

    def _remove_special_chars(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """移除特殊字符（保留基本标点和字母数字）"""
        # 检测特殊字符
        special_pattern = r'[^\w\s\'".,!?;:()\[\]{}-]'
        special_chars = re.findall(special_pattern, text)

        if special_chars:
            # 只保留可打印 ASCII + 基本标点
            text = re.sub(special_pattern, '', text)

            # 统计移除的字符
            char_count = {}
            for char in special_chars:
                char_count[char] = char_count.get(char, 0) + 1

            return text, char_count

        return text, {}

    def extract_emotion_hint(self, text: str) -> Tuple[str, Optional[str]]:
        """
        提取情感提示（如 [crying], [angry]）

        Args:
            text: 文本

        Returns:
            (清理后的文本, 情感提示)
        """
        emotion_pattern = r'\[([^\]]+)\]'
        match = re.search(emotion_pattern, text)

        if match:
            emotion_hint = match.group(1)
            cleaned_text = re.sub(emotion_pattern, '', text).strip()
            return cleaned_text, emotion_hint

        return text, None

    def extract_speaker_hint(self, text: str) -> Tuple[str, Optional[str]]:
        """
        提取说话人提示（如 Walter:, "Walter: ...）

        Args:
            text: 文本

        Returns:
            (清理后的文本, 说话人提示)
        """
        # 尝试各种说话人格式
        speaker_patterns = [
            r'^([^:]+):\s*(.+)$',  # Walter: text
            r'^"([^:]+)":\s*(.+)$',  # "Walter": text
            r'^([A-Z][A-Z\s]+?)\n(.+)$',  # WALTER\n（换行）text
        ]

        for pattern in speaker_patterns:
            match = re.match(pattern, text.strip(), re.MULTILINE)
            if match:
                speaker = match.group(1).strip()
                dialogue = match.group(2).strip()
                return dialogue, speaker

        return text, None
