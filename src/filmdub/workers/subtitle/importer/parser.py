"""
字幕解析器 - 支持多种字幕格式的解析和转换
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Tuple
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
    CJK_PATTERN = re.compile(r'[\u4e00-\u9fff]')
    LATIN_PATTERN = re.compile(r'[A-Za-z]')

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
        # 字段顺序: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
        # Text 是最后一个字段，可能包含逗号，必须用贪婪匹配取行剩余部分
        dialogue_pattern = re.compile(
            r'^Dialogue:\s*[^,]*,'
            r'(\d+):(\d+):(\d+)\.(\d+),'
            r'(\d+):(\d+):(\d+)\.(\d+),'
            r'[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,'  # Style, Name, MarginL/R/V, Effect
            r'(.*)$'  # Text（含逗号）
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

    def classify_line(self, line: str) -> Optional[str]:
        """按内容判断单行语言：含 CJK 视为中文，否则含拉丁字母视为英文"""
        if self.CJK_PATTERN.search(line):
            return 'zh'
        if self.LATIN_PATTERN.search(line):
            return 'en'
        return None

    def is_bilingual(self, entries: List[SubtitleEntry]) -> bool:
        """检测条目中是否存在中英混排（同一行内同时含 CJK 与拉丁字母）"""
        return any(
            self.CJK_PATTERN.search(e.text) and self.LATIN_PATTERN.search(e.text)
            for e in entries
        )

    def _split_mixed_line(self, line: str) -> Tuple[str, str]:
        """
        将一行中英混排文本切成（中文段, 英文段）。

        切分点取「其后不再出现 CJK 的首个拉丁字母」位置；若中英交错
        （拉丁段之后又出现 CJK），则无法可靠切分，整行归中文侧返回。
        纯英文行返回 ("", 原行)，纯中文/无字母行返回 (原行, "")。
        """
        latin_positions = [m.start() for m in self.LATIN_PATTERN.finditer(line)]
        if not latin_positions:
            return line, ""

        last_cjk = max(
            (m.start() for m in self.CJK_PATTERN.finditer(line)),
            default=-1,
        )
        first_latin = latin_positions[0]
        if last_cjk < first_latin:
            return line[:first_latin], line[first_latin:]
        return line, ""

    def split_bilingual(
        self, entries: List[SubtitleEntry]
    ) -> Tuple[List[SubtitleEntry], List[SubtitleEntry]]:
        """
        将双语字幕条目拆分为纯英文与纯中文两组。

        兼容两种排版：多行字幕（解析后按换行分隔）与单行混排
        （清洗阶段换行被折叠为空格）。拆出的条目沿用原时间轴。
        """
        en_entries: List[SubtitleEntry] = []
        zh_entries: List[SubtitleEntry] = []

        def _emit(seg: str, bucket: List[SubtitleEntry]) -> None:
            if seg.strip():
                bucket.append(SubtitleEntry(
                    index=len(bucket), start=entry.start, end=entry.end,
                    text=seg.strip()
                ))

        for entry in entries:
            for line in entry.text.split('\n'):
                zh_seg, en_seg = self._split_mixed_line(line)
                _emit(zh_seg, zh_entries)
                if not self.CJK_PATTERN.search(en_seg):
                    _emit(en_seg, en_entries)

        logger.info(f"Split bilingual subtitle: {len(entries)} entries -> "
                    f"{len(en_entries)} en / {len(zh_entries)} zh")
        return en_entries, zh_entries

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
