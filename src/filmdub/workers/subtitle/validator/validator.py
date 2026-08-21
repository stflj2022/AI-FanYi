"""
字幕验证器 - 验证字幕质量
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..importer.parser import SubtitleEntry
from ...subtitle.config import SubtitleConfig

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """验证问题严重程度"""
    ERROR = "error"  # 错误，必须修复
    WARNING = "warning"  # 警告，建议修复
    INFO = "info"  # 信息，仅供参考


@dataclass
class ValidationIssue:
    """验证问题"""
    entry_index: Optional[int]  # 字幕索引，None 表示整体问题
    severity: ValidationSeverity
    issue_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    can_auto_fix: bool = False


@dataclass
class ValidationReport:
    """验证报告"""
    total_entries: int
    valid_entries: int
    issues: List[ValidationIssue]
    quality_score: float

    @property
    def error_count(self) -> int:
        """错误数量"""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """警告数量"""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)


class SubtitleValidator:
    """字幕验证器"""

    def __init__(self, config: SubtitleConfig):
        """
        初始化验证器

        Args:
            config: 字幕配置
        """
        self.config = config

    def validate(
        self,
        entries: List[SubtitleEntry],
        video_duration: Optional[float] = None
    ) -> ValidationReport:
        """
        验证字幕

        Args:
            entries: 字幕条目列表
            video_duration: 视频时长（秒）

        Returns:
            验证报告
        """
        issues = []

        # 1. 基本验证
        for entry in entries:
            entry_issues = self._validate_entry(entry)
            issues.extend(entry_issues)

        # 2. 时间轴验证
        time_issues = self._validate_timeline(entries, video_duration)
        issues.extend(time_issues)

        # 3. 内容验证
        content_issues = self._validate_content(entries)
        issues.extend(content_issues)

        # 4. 重叠验证
        overlap_issues = self._validate_overlaps(entries)
        issues.extend(overlap_issues)

        # 计算错误数量
        error_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        valid_count = len(entries) - error_count
        quality_score = valid_count / len(entries) if entries else 0.0

        report = ValidationReport(
            total_entries=len(entries),
            valid_entries=valid_count,
            issues=issues,
            quality_score=quality_score
        )

        logger.info(f"Validation complete: {valid_count}/{len(entries)} valid, "
                   f"{report.error_count} errors, {report.warning_count} warnings, "
                   f"quality_score={quality_score:.2f}")

        return report

    def _validate_entry(self, entry: SubtitleEntry) -> List[ValidationIssue]:
        """验证单个字幕条目"""
        issues = []

        # 检查时间
        if entry.start >= entry.end:
            issues.append(ValidationIssue(
                entry_index=entry.index,
                severity=ValidationSeverity.ERROR,
                issue_type="invalid_time",
                message=f"Start time ({entry.start}) >= end time ({entry.end})",
                details={"start": entry.start, "end": entry.end},
                can_auto_fix=False
            ))

        # 检查持续时间
        duration = entry.duration()
        if duration < self.config.min_subtitle_duration:
            issues.append(ValidationIssue(
                entry_index=entry.index,
                severity=ValidationSeverity.WARNING,
                issue_type="too_short",
                message=f"Duration ({duration:.2f}s) is too short",
                details={"duration": duration},
                can_auto_fix=True
            ))
        elif duration > self.config.max_subtitle_duration:
            issues.append(ValidationIssue(
                entry_index=entry.index,
                severity=ValidationSeverity.WARNING,
                issue_type="too_long",
                message=f"Duration ({duration:.2f}s) is too long",
                details={"duration": duration},
                can_auto_fix=True
            ))

        # 检查空文本
        if not entry.text or not entry.text.strip():
            issues.append(ValidationIssue(
                entry_index=entry.index,
                severity=ValidationSeverity.ERROR,
                issue_type="empty_text",
                message="Empty subtitle text",
                can_auto_fix=True
            ))

        # 检查异常字符
        if '\ufffd' in entry.text:  # 替换字符
            issues.append(ValidationIssue(
                entry_index=entry.index,
                severity=ValidationSeverity.WARNING,
                issue_type="replacement_char",
                message="Contains replacement character (�)",
                can_auto_fix=False
            ))

        return issues

    def _validate_timeline(
        self,
        entries: List[SubtitleEntry],
        video_duration: Optional[float]
    ) -> List[ValidationIssue]:
        """验证时间轴"""
        issues = []

        if not entries:
            return issues

        # 检查时间顺序
        for i in range(1, len(entries)):
            if entries[i-1].end > entries[i].start:
                issues.append(ValidationIssue(
                    entry_index=entries[i].index,
                    severity=ValidationSeverity.ERROR,
                    issue_type="time_order",
                    message=f"Entry {entries[i-1].index} ends after entry {entries[i].index} starts",
                    details={
                        "prev_end": entries[i-1].end,
                        "current_start": entries[i].start
                    },
                    can_auto_fix=False
                ))

        # 检查与视频时长的匹配
        if video_duration:
            last_end = entries[-1].end
            diff = abs(last_end - video_duration)

            if diff > self.config.max_duration_diff:
                issues.append(ValidationIssue(
                    entry_index=None,
                    severity=ValidationSeverity.WARNING,
                    issue_type="duration_mismatch",
                    message=f"Subtitle duration ({last_end:.2f}s) differs from video ({video_duration:.2f}s)",
                    details={
                        "subtitle_duration": last_end,
                        "video_duration": video_duration,
                        "diff": diff
                    },
                    can_auto_fix=False
                ))

        return issues

    def _validate_content(self, entries: List[SubtitleEntry]) -> List[ValidationIssue]:
        """验证内容"""
        issues = []

        for entry in entries:
            text = entry.text

            # 检查是否只包含标点或符号
            if not re.search(r'[a-zA-Z\u4e00-\u9fff]', text):
                issues.append(ValidationIssue(
                    entry_index=entry.index,
                    severity=ValidationSeverity.WARNING,
                    issue_type="no_letters",
                    message="Subtitle contains no letters or Chinese characters",
                    can_auto_fix=True
                ))

            # 检查是否只是重复字符
            if len(set(text)) <= 2 and len(text) > 5:
                issues.append(ValidationIssue(
                    entry_index=entry.index,
                    severity=ValidationSeverity.WARNING,
                    issue_type="repeated_chars",
                    message="Subtitle appears to be repeated characters",
                    can_auto_fix=False
                ))

        return issues

    def _validate_overlaps(self, entries: List[SubtitleEntry]) -> List[ValidationIssue]:
        """验证重叠"""
        issues = []

        for i in range(1, len(entries)):
            prev_end = entries[i-1].end
            curr_start = entries[i].start

            # 允许很小的重叠（最多0.1秒）
            if prev_end > curr_start + 0.1:
                overlap = prev_end - curr_start
                issues.append(ValidationIssue(
                    entry_index=entries[i].index,
                    severity=ValidationSeverity.WARNING,
                    issue_type="overlap",
                    message=f"Overlaps with previous subtitle by {overlap:.2f}s",
                    details={
                        "overlap": overlap,
                        "prev_entry": entries[i-1].index
                    },
                    can_auto_fix=True
                ))

        return issues

    def fix_auto_issues(
        self,
        entries: List[SubtitleEntry],
        report: ValidationReport
    ) -> List[SubtitleEntry]:
        """
        自动修复可修复的问题

        Args:
            entries: 字幕条目列表
            report: 验证报告

        Returns:
            修复后的字幕条目列表
        """
        fixed_entries = [e for e in entries]  # 深拷贝

        for issue in report.issues:
            if not issue.can_auto_fix or issue.entry_index is None:
                continue

            # 找到对应的条目
            entry = next((e for e in fixed_entries if e.index == issue.entry_index), None)
            if not entry:
                continue

            # 根据问题类型修复
            if issue.issue_type == "empty_text":
                # 标记为删除
                fixed_entries.remove(entry)
                logger.info(f"Fixed empty text at entry {entry.index}: removed")

            elif issue.issue_type == "too_short":
                # 与下一条合并（如果存在）
                next_entry = next((e for e in fixed_entries if e.index > entry.index), None)
                if next_entry:
                    entry.text = f"{entry.text} {next_entry.text}"
                    entry.end = next_entry.end
                    fixed_entries.remove(next_entry)
                    logger.info(f"Fixed too short entry {entry.index}: merged with next")

            # 注意：too_long 和 overlap 需要更复杂的逻辑，这里暂不处理

        logger.info(f"Auto-fixed {len(entries) - len(fixed_entries)} entries")
        return fixed_entries

    def calculate_quality_score(self, report: ValidationReport) -> float:
        """
        计算质量评分

        Args:
            report: 验证报告

        Returns:
            质量评分 (0-1)
        """
        if report.total_entries == 0:
            return 0.0

        # 基础分数
        score = report.quality_score

        # 错误惩罚
        error_penalty = report.error_count / report.total_entries * 0.5
        score -= error_penalty

        # 警告惩罚
        warning_penalty = report.warning_count / report.total_entries * 0.1
        score -= warning_penalty

        # 确保在 0-1 范围内
        return max(0.0, min(1.0, score))


import re  # 放在文件末尾
