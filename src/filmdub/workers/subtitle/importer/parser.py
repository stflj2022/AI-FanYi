"""
字幕解析器 - 支持多种字幕格式的解析和转换
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..config import SubtitleFormat

logger = logging.getLogger(__name__)


@dataclass
class SubtitleEntry:
    """字幕条目"""
    index: int
    start: float  # 秒
    end: float  # 秒
    text: str

    def duration(self) -> float:
        """获取持续时间"""
        return self.end - self.start


class SubtitleParser:
    """字幕解析器"""

    # 时间戳正则
    SRT_TIME_PATTERN = re.compile(
        r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})'
    )
    VTT_TIME_PATTERN = re.compile(
        r'(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})'
    )

    def __init__(self):
        """初始化解析器"""
        pass

    def parse(self, subtitle_path: Path) -> List[SubtitleEntry]:
        """
        解析字幕文件

        Args:
            subtitle_path: 字幕文件路径

        Returns:
            字幕条目列表
        """
        if not subtitle_path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")

        # 根据扩展名选择解析器
        suffix = subtitle_path.suffix.lower()

        if suffix == '.srt':
            return self._parse_srt(subtitle_path)
        elif suffix == '.vtt':
            return self._parse_vtt(subtitle_path)
        elif suffix in ('.ass', '.ssa'):
            return self._parse_ass(subtitle_path)
        else:
            # 默认尝试 SRT 解析
            logger.warning(f"Unknown subtitle format: {suffix}, trying SRT parser")
            return self._parse_srt(subtitle_path)

    def _parse_srt(self, subtitle_path: Path) -> List[SubtitleEntry]:
        """解析 SRT 格式"""
        entries = []
        content = self._read_file(subtitle_path)

        # 分割字幕块
        blocks = re.split(r'\n\s*\n', content.strip())

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            try:
                entry = self._parse_srt_block(block)
                if entry:
                    entries.append(entry)
            except Exception as e:
                logger.warning(f"Failed to parse SRT block: {block[:50]}... Error: {e}")

        logger.info(f"Parsed {len(entries)} SRT entries from {subtitle_path.name}")
        return entries

    def _parse_srt_block(self, block: str) -> Optional[SubtitleEntry]:
        """解析单个 SRT 块"""
        lines = block.split('\n')

        if len(lines) < 2:
            return None

        # 第一行是序号
        try:
            index = int(lines[0].strip())
        except ValueError:
            return None

        # 第二行是时间戳
        time_match = self.SRT_TIME_PATTERN.search(lines[1])
        if not time_match:
            return None

        start = self._parse_timestamp(
            time_match.group(1), time_match.group(2), time_match.group(3), time_match.group(4)
        )
        end = self._parse_timestamp(
            time_match.group(5), time_match.group(6), time_match.group(7), time_match.group(8)
        )

        # 剩余行是文本
        text = '\n'.join(lines[2:]).strip()
        text = self._clean_text(text)

        return SubtitleEntry(index=index, start=start, end=end, text=text)

    def _parse_vtt(self, subtitle_path: Path) -> List[SubtitleEntry]:
        """解析 WebVTT 格式"""
        entries = []
        content = self._read_file(subtitle_path)

        # 移除 WEBVTT 头
        lines = content.split('\n')

        # 跳过头
        start_idx = 0
        for i, line in enumerate(lines):
            if line.strip() == 'WEBVTT':
                start_idx = i + 1
                break

        entries = []
        current_entry = None
        current_text = []

        for line in lines[start_idx:]:
            line = line.strip()

            # 空行表示条目结束
            if not line:
                if current_entry:
                    current_entry.text = '\n'.join(current_text).strip()
                    entries.append(current_entry)
                    current_entry = None
                    current_text = []
                continue

            # 检查时间戳行
            time_match = self.VTT_TIME_PATTERN.search(line)
            if time_match:
                if current_entry:
                    current_entry.text = '\n'.join(current_text).strip()
                    entries.append(current_entry)

                start = self._parse_timestamp_vtt(
                    time_match.group(1), time_match.group(2), time_match.group(3), time_match.group(4)
                )
                end = self._parse_timestamp_vtt(
                    time_match.group(5), time_match.group(6), time_match.group(7), time_match.group(8)
                )

                current_entry = SubtitleEntry(
                    index=len(entries),
                    start=start,
                    end=end,
                    text=""
                )
                current_text = []
            else:
                if current_entry is not None:
                    current_text.append(line)

        # 最后一个条目
        if current_entry:
            current_entry.text = '\n'.join(current_text).strip()
            entries.append(current_entry)

        logger.info(f"Parsed {len(entries)} VTT entries from {subtitle_path.name}")
        return entries

    def _parse_ass(self, subtitle_path: Path) -> List[SubtitleEntry]:
        """
        解析 ASS/SSA 格式

        注意：这是一个简化版解析器，只处理基本对话
        """
        entries = []
        content = self._read_file(subtitle_path)

        # ASS 格式的对话行以 Dialogue: 开头
        dialogue_pattern = re.compile(
            r'^Dialogue:\s*\d+,'
            r'(\d+):(\d+):(\d+)\.(\d+),'
            r'(\d+):(\d+):(\d+)\.(\d+),'
            r'[^,]*,[^,]*,'  # Style, Name
            r'([^,]*)'  # Text
        )

        for line in content.split('\n'):
            line = line.strip()

            # 跳过注释和格式定义
            if not line.startswith('Dialogue:'):
                continue

            match = dialogue_pattern.match(line)
            if not match:
                continue

            start = self._parse_timestamp_ass(
                match.group(1), match.group(2), match.group(3), match.group(4)
            )
            end = self._parse_timestamp_ass(
                match.group(5), match.group(6), match.group(7), match.group(8)
            )

            # 清理 ASS 标签
            text = match.group(9)
            text = re.sub(r'\{[^}]+\}', '', text)  # 移除 {...} 标签
            text = re.sub(r'\\[nN]', '\n', text)  # 转换换行符
            text = self._clean_text(text)

            if text.strip():
                entries.append(SubtitleEntry(
                    index=len(entries),
                    start=start,
                    end=end,
                    text=text
                ))

        logger.info(f"Parsed {len(entries)} ASS entries from {subtitle_path.name}")
        return entries

    def _read_file(self, file_path: Path) -> str:
        """读取文件，自动检测编码"""
        encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'big5', 'latin-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        # 如果所有编码都失败，使用 latin-1 并忽略错误
        with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
            return f.read()

    def _parse_timestamp(self, hours: str, minutes: str, seconds: str, ms: str) -> float:
        """解析 SRT 时间戳"""
        return (
            int(hours) * 3600 +
            int(minutes) * 60 +
            int(seconds) +
            int(ms) / 1000
        )

    def _parse_timestamp_vtt(self, hours: str, minutes: str, seconds: str, ms: str) -> float:
        """解析 VTT 时间戳"""
        return (
            int(hours) * 3600 +
            int(minutes) * 60 +
            int(seconds) +
            int(ms) / 1000
        )

    def _parse_timestamp_ass(self, hours: str, minutes: str, seconds: str, cs: str) -> float:
        """解析 ASS 时间戳（厘秒）"""
        return (
            int(hours) * 3600 +
            int(minutes) * 60 +
            int(seconds) +
            int(cs) / 100
        )

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        # 移除多余的空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def to_jsonl(self, entries: List[SubtitleEntry], output_path: Path, language: str = "en") -> None:
        """
        将字幕条目导出为 JSONL 格式

        Args:
            entries: 字幕条目列表
            output_path: 输出文件路径
            language: 语言代码
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in entries:
                line = {
                    "id": f"dlg_{entry.index:06d}",
                    "start": entry.start,
                    "end": entry.end,
                    "text": entry.text,
                    "language": language
                }
                f.write(json.dumps(line, ensure_ascii=False) + '\n')

        logger.info(f"Exported {len(entries)} entries to {output_path}")

    def from_jsonl(self, jsonl_path: Path) -> List[SubtitleEntry]:
        """
        从 JSONL 文件加载字幕条目

        Args:
            jsonl_path: JSONL 文件路径

        Returns:
            字幕条目列表
        """
        entries = []

        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())
                entry = SubtitleEntry(
                    index=int(data['id'].split('_')[1]),
                    start=data['start'],
                    end=data['end'],
                    text=data['text']
                )
                entries.append(entry)

        logger.info(f"Loaded {len(entries)} entries from {jsonl_path}")
        return entries


import json  # 放在文件末尾，避免与上面 import 冲突
