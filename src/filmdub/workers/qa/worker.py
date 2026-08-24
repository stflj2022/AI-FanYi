"""
M13 QA Checker

对生成的中文配音视频进行技术质量和配音质量自动检查
"""
from __future__ import annotations

import subprocess
import json
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import re

from .config import M13Config
from .models import (
    QAInput,
    QAResult,
    TechnicalQuality,
    VoiceQuality,
    QAIssue,
    QAIssueSeverity,
    QAIssueCategory,
)

logger = logging.getLogger(__name__)


class QAChecker:
    """QA 检查器"""

    def __init__(self, config: M13Config = None):
        """
        初始化 QA 检查器

        Args:
            config: M13 配置
        """
        self.config = config or M13Config()
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """确保输出目录存在"""
        os.makedirs(self.config.output_dir, exist_ok=True)

    def check(self, input_data: QAInput) -> QAResult:
        """
        执行 QA 检查

        Args:
            input_data: QA 输入

        Returns:
            QA 结果
        """
        try:
            logger.info(f"开始 QA 检查: {input_data.video_file}")

            # 验证输入
            self._validate_input(input_data)

            # 技术质量检查
            technical_quality = self._check_technical_quality(input_data)

            # 配音质量检查
            voice_quality = self._check_voice_quality(input_data)

            # 收集所有问题
            issues = []
            issues.extend(technical_quality.issues if hasattr(technical_quality, 'issues') else [])
            issues.extend(voice_quality.issues if hasattr(voice_quality, 'issues') else [])

            # 创建结果
            result = QAResult(
                video_file=input_data.video_file,
                technical_quality=technical_quality,
                voice_quality=voice_quality,
                issues=issues,
                duration_seconds=technical_quality.duration
            )

            # 计算统计和评分
            result.calculate_statistics()
            result.calculate_overall_score()

            # 判断是否通过
            if input_data.strict_mode:
                # 严格模式：所有问题都导致失败
                result.success = len(issues) == 0
            else:
                # 非严格模式：只有严重和高优先级问题导致失败
                critical_or_high = result.critical_issues + result.high_issues
                result.success = critical_or_high == 0

            # 写出 QA 报告文件
            report_path = self._write_report(result)
            if report_path:
                result.report_path = report_path

            logger.info(f"QA 检查完成: 评分={result.overall_score:.1f}, 问题={len(issues)}, 通过={result.success}")

            return result

        except Exception as e:
            logger.error(f"QA 检查失败: {e}", exc_info=True)
            # 返回失败结果
            return QAResult(
                success=False,
                overall_score=0.0,
                video_file=input_data.video_file,
                technical_quality=TechnicalQuality(
                    passed=False,
                    score=0.0,
                    duration=0.0,
                    size_bytes=0
                ),
                voice_quality=VoiceQuality(
                    passed=False,
                    score=0.0
                ),
                issues=[
                    QAIssue(
                        category=QAIssueCategory.OTHER,
                        severity=QAIssueSeverity.CRITICAL,
                        title="QA 检查失败",
                        description=f"检查过程出错: {str(e)}"
                    )
                ]
            )

    def _validate_input(self, input_data: QAInput):
        """验证输入"""
        if not os.path.exists(input_data.video_file):
            raise FileNotFoundError(f"视频文件不存在: {input_data.video_file}")

        if input_data.original_video and not os.path.exists(input_data.original_video):
            logger.warning(f"原始视频文件不存在: {input_data.original_video}")

        if input_data.character_db and not os.path.exists(input_data.character_db):
            logger.warning(f"人物数据库文件不存在: {input_data.character_db}")

        if input_data.dialogue_timeline and not os.path.exists(input_data.dialogue_timeline):
            logger.warning(f"对白时间轴文件不存在: {input_data.dialogue_timeline}")

    def _check_technical_quality(self, input_data: QAInput) -> TechnicalQuality:
        """
        检查技术质量

        Args:
            input_data: QA 输入

        Returns:
            技术质量结果
        """
        issues: List[QAIssue] = []

        # 获取视频信息
        video_info = self._get_video_info(input_data.video_file)

        if not video_info:
            # 无法获取视频信息
            return TechnicalQuality(
                passed=False,
                score=0.0,
                duration=0.0,
                size_bytes=0
            )

        # 提取视频流信息
        video_stream = self._get_video_stream(video_info)
        audio_stream = self._get_audio_stream(video_info)

        # 检查视频质量
        if video_stream:
            width = video_stream.get("width")
            height = video_stream.get("height")
            fps = self._parse_fps(video_stream.get("r_frame_rate"))

            # 分辨率检查
            if width and width < self.config.min_video_width:
                issues.append(QAIssue(
                    category=QAIssueCategory.TECHNICAL,
                    severity=QAIssueSeverity.MEDIUM,
                    title="视频分辨率过低",
                    description=f"视频宽度 {width}px 低于最小要求 {self.config.min_video_width}px",
                    suggestion=f"建议使用至少 {self.config.min_video_width}x{int(width/height*self.config.min_video_width)} 的分辨率"
                ))

            if height and height < self.config.min_video_height:
                issues.append(QAIssue(
                    category=QAIssueCategory.TECHNICAL,
                    severity=QAIssueSeverity.MEDIUM,
                    title="视频分辨率过低",
                    description=f"视频高度 {height}px 低于最小要求 {self.config.min_video_height}px"
                ))

            # 帧率检查
            if fps:
                if fps < self.config.min_fps:
                    issues.append(QAIssue(
                        category=QAIssueCategory.TECHNICAL,
                        severity=QAIssueSeverity.MEDIUM,
                        title="视频帧率过低",
                        description=f"视频帧率 {fps:.2f}fps 低于最小要求 {self.config.min_fps}fps",
                        suggestion=f"建议使用至少 {self.config.min_fps}fps 的帧率"
                    ))
                elif fps > self.config.max_fps:
                    issues.append(QAIssue(
                        category=QAIssueCategory.TECHNICAL,
                        severity=QAIssueSeverity.LOW,
                        title="视频帧率过高",
                        description=f"视频帧率 {fps:.2f}fps 高于推荐值 {self.config.max_fps}fps"
                    ))

        # 检查音频质量
        if audio_stream:
            try:
                sample_rate = int(audio_stream.get("sample_rate"))
            except (TypeError, ValueError):
                sample_rate = None
            try:
                channels = int(audio_stream.get("channels"))
            except (TypeError, ValueError):
                channels = None

            if sample_rate and sample_rate < self.config.min_audio_sample_rate:
                issues.append(QAIssue(
                    category=QAIssueCategory.TECHNICAL,
                    severity=QAIssueSeverity.MEDIUM,
                    title="音频采样率过低",
                    description=f"音频采样率 {sample_rate}Hz 低于最小要求 {self.config.min_audio_sample_rate}Hz",
                    suggestion=f"建议使用至少 {self.config.min_audio_sample_rate}Hz 的采样率"
                ))

            if channels and channels < self.config.min_audio_channels:
                issues.append(QAIssue(
                    category=QAIssueCategory.TECHNICAL,
                    severity=QAIssueSeverity.LOW,
                    title="音频声道数不足",
                    description=f"音频声道数 {channels} 低于推荐值 {self.config.min_audio_channels}",
                    suggestion=f"建议使用至少 {self.config.min_audio_channels} 声道（立体声）"
                ))

        # 检查音画同步
        sync_offset = self._check_audio_video_sync(input_data.video_file)
        if abs(sync_offset) > self.config.sync_tolerance_seconds:
            issues.append(QAIssue(
                category=QAIssueCategory.SYNC,
                severity=QAIssueSeverity.HIGH,
                title="音画同步偏差",
                description=f"音画同步偏差 {sync_offset:.3f}s 超过容差 {self.config.sync_tolerance_seconds}s",
                suggestion="使用音视频同步工具调整时间轴"
            ))

        # 响度检测（EBU R128 / ITU-R BS.1770）
        loudness_lufs, peak_db = self._check_loudness(input_data.video_file)
        if loudness_lufs is not None and abs(loudness_lufs - self.config.target_lufs) > self.config.lufs_tolerance:
            issues.append(QAIssue(
                category=QAIssueCategory.TECHNICAL,
                severity=QAIssueSeverity.MEDIUM,
                title="响度不符合标准",
                description=f"音频响度 {loudness_lufs:.1f} LUFS，目标 {self.config.target_lufs} LUFS（容差 ±{self.config.lufs_tolerance} LUFS）",
                suggestion="使用 loudnorm 进行响度归一化（EBU R128）"
            ))

        # 静音检测
        silence_issues = self._check_silence(input_data.video_file)
        issues.extend(silence_issues)

        # 爆音/削波检测
        if peak_db is not None and peak_db > self.config.peak_db:
            issues.append(QAIssue(
                category=QAIssueCategory.TECHNICAL,
                severity=QAIssueSeverity.HIGH,
                title="音频爆音/削波",
                description=f"音频峰值 {peak_db:.1f} dB 超过安全阈值 {self.config.peak_db} dB",
                suggestion="降低增益或使用限幅器避免削波"
            ))

        # 计算技术质量评分
        score = self._calculate_technical_score(issues, video_info)

        # 创建技术质量结果
        return TechnicalQuality(
            passed=len([i for i in issues if i.severity in [QAIssueSeverity.CRITICAL, QAIssueSeverity.HIGH]]) == 0,
            score=score,
            video_codec=video_stream.get("codec_name") if video_stream else None,
            video_width=video_stream.get("width") if video_stream else None,
            video_height=video_stream.get("height") if video_stream else None,
            video_bitrate=int(video_stream.get("bit_rate", 0)) if video_stream else None,
            fps=self._parse_fps(video_stream.get("r_frame_rate")) if video_stream else None,
            audio_codec=audio_stream.get("codec_name") if audio_stream else None,
            audio_sample_rate=int(audio_stream.get("sample_rate")) if audio_stream and str(audio_stream.get("sample_rate", "")).isdigit() else None,
            audio_channels=int(audio_stream.get("channels")) if audio_stream and str(audio_stream.get("channels", "")).isdigit() else None,
            audio_bitrate=int(audio_stream.get("bit_rate", 0)) if audio_stream else None,
            sync_offset=sync_offset,
            sync_issues=1 if abs(sync_offset) > self.config.sync_tolerance_seconds else 0,
            loudness_lufs=loudness_lufs,
            peak_db=peak_db,
            duration=float(video_info.get("format", {}).get("duration", 0)),
            size_bytes=int(video_info.get("format", {}).get("size", 0))
        )

    def _check_voice_quality(self, input_data: QAInput) -> VoiceQuality:
        """
        检查配音质量

        Args:
            input_data: QA 输入

        Returns:
            配音质量结果
        """
        issues: List[QAIssue] = []

        # 加载对白时间轴（如果存在）
        dialogues = []
        if input_data.dialogue_timeline and os.path.exists(input_data.dialogue_timeline):
            try:
                with open(input_data.dialogue_timeline, 'r', encoding='utf-8') as f:
                    dialogues = json.load(f)
            except Exception as e:
                logger.warning(f"加载对白时间轴失败: {e}")

        # 音色一致性检查
        voice_consistency_score, voice_issues = self._check_voice_consistency(dialogues, input_data.character_db)
        issues.extend(voice_issues)

        # 情绪匹配检查
        emotion_match_score, emotion_issues = self._check_emotion_match(dialogues)
        issues.extend(emotion_issues)

        # 语速合理性检查
        speech_rate_score, speech_rate_issues = self._check_speech_rate(dialogues)
        issues.extend(speech_rate_issues)

        # 翻译质量检查（基础检查）
        translation_score, translation_issues = self._check_translation_quality(dialogues)
        issues.extend(translation_issues)

        # 对白完整性检查（漏台词/重复台词）
        dialogue_completeness, dialogue_issues = self._check_missing_duplicate_dialogue(dialogues)
        issues.extend(dialogue_issues)

        # 人物错配检查（说话人 vs 计划人物）
        mismatch_score, mismatch_issues = self._check_character_mismatch(dialogues, input_data.character_db)
        issues.extend(mismatch_issues)

        # 计算配音质量评分
        score = (
            voice_consistency_score * 0.25 +
            emotion_match_score * 0.25 +
            speech_rate_score * 0.20 +
            translation_score * 0.15 +
            dialogue_completeness * 0.10 +
            mismatch_score * 0.05
        )

        # 创建配音质量结果
        return VoiceQuality(
            passed=len([i for i in issues if i.severity in [QAIssueSeverity.CRITICAL, QAIssueSeverity.HIGH]]) == 0,
            score=score,
            voice_consistency=voice_consistency_score,
            voice_issues=len(voice_issues),
            emotion_match=emotion_match_score,
            emotion_issues=len(emotion_issues),
            speech_rate_reasonable=speech_rate_score,
            speech_rate_issues=len(speech_rate_issues),
            translation_quality=translation_score,
            translation_issues=len(translation_issues),
            dialogue_completeness=dialogue_completeness,
            dialogue_issues=len(dialogue_issues),
            character_mismatch_score=mismatch_score,
            mismatch_issues=len(mismatch_issues)
        )

    def _get_video_info(self, video_file: str) -> Optional[Dict[str, Any]]:
        """获取视频文件信息"""
        try:
            cmd = [
                self.config.ffprobe_path,
                "-v", "error",
                "-show_format",
                "-show_streams",
                "-of", "json",
                video_file
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"FFprobe 执行失败: {result.stderr}")
                return None

            return json.loads(result.stdout)

        except subprocess.TimeoutExpired:
            logger.error("FFprobe 执行超时")
            return None
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
            return None

    def _get_video_stream(self, video_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取视频流"""
        if "streams" not in video_info:
            return None
        for stream in video_info["streams"]:
            if stream.get("codec_type") == "video":
                return stream
        return None

    def _get_audio_stream(self, video_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取音频流"""
        if "streams" not in video_info:
            return None
        for stream in video_info["streams"]:
            if stream.get("codec_type") == "audio":
                return stream
        return None

    def _parse_fps(self, fps_str: Optional[str]) -> Optional[float]:
        """解析帧率字符串"""
        if not fps_str:
            return None
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                return float(num) / float(den)
            return float(fps_str)
        except (ValueError, ZeroDivisionError):
            return None

    def _check_audio_video_sync(self, video_file: str) -> float:
        """
        检查音画同步

        使用 FFmpeg 分析音视频时间戳

        Returns:
            同步偏差（秒），正数表示音频延迟，负数表示视频延迟
        """
        try:
            # 简单的同步检查：比较音视频流的开始时间
            cmd = [
                self.config.ffprobe_path,
                "-v", "error",
                "-show_entries", "stream=start_time,duration",
                "-of", "csv=p=0",
                video_file
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return 0.0

            lines = result.stdout.strip().split('\n')
            video_start = None
            audio_start = None

            # FFprobe 返回流信息，第一个是视频，第二个是音频
            for i, line in enumerate(lines):
                parts = line.split(',')
                if len(parts) >= 2:
                    start_time = float(parts[0]) if parts[0] else 0.0
                    # 根据流索引判断类型（0=视频，1=音频）
                    if i == 0:
                        video_start = start_time
                    elif i == 1:
                        audio_start = start_time

            if video_start is not None and audio_start is not None:
                return audio_start - video_start

        except Exception as e:
            logger.warning(f"音画同步检查失败: {e}")

        return 0.0

    def _run_ffmpeg_capture(self, cmd: List[str]) -> Optional[str]:
        """
        运行 ffmpeg 并捕获输出（ffmpeg 分析日志输出到 stderr）

        Args:
            cmd: 命令参数列表

        Returns:
            stderr 文本，失败返回 None
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
            )
            return result.stderr or result.stdout or ""
        except subprocess.TimeoutExpired:
            logger.warning("ffmpeg 执行超时")
            return None
        except Exception as e:
            logger.warning(f"ffmpeg 执行失败: {e}")
            return None

    def _parse_ebur128_loudness(self, output: str) -> Optional[float]:
        """解析 ebur128 输出的综合响度（LUFS）"""
        m = re.search(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", output)
        return float(m.group(1)) if m else None

    def _parse_dbfs_peak(self, output: str) -> Optional[float]:
        """解析 ebur128 输出的峰值（dBFS）"""
        m = re.search(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", output)
        return float(m.group(1)) if m else None

    def _parse_volumedetect(self, output: str, key: str) -> Optional[float]:
        """解析 volumedetect 输出的指标（mean_volume/max_volume）"""
        m = re.search(rf"{key}:\s*(-?\d+(?:\.\d+)?)\s*dB", output)
        return float(m.group(1)) if m else None

    def _check_loudness(self, video_file: str) -> Tuple[Optional[float], Optional[float]]:
        """
        检测音频响度（LUFS）和峰值（dB）

        优先使用 ebur128 滤波器（ITU-R BS.1770 / EBU R128），
        失败时回退到 volumedetect（mean_volume 近似响度）。

        Returns:
            (loudness_lufs, peak_db)
        """
        # 方式一：ebur128
        cmd = [
            self.config.ffmpeg_path, "-hide_banner", "-nostats", "-i", video_file,
            "-af", "ebur128", "-f", "null", "-",
        ]
        output = self._run_ffmpeg_capture(cmd)
        if output:
            loudness = self._parse_ebur128_loudness(output)
            peak = self._parse_dbfs_peak(output)
            if loudness is not None:
                return loudness, peak

        # 方式二：volumedetect（无 ebur128 时回退）
        # 注意：volumedetect 的 mean_volume 是 dBFS 均值，并非 ITU-R BS.1770 的 LUFS，
        # 此处仅作为响度的近似值（近似 LUFS），并同时返回准确的峰值（max_volume）。
        cmd = [
            self.config.ffmpeg_path, "-hide_banner", "-nostats", "-i", video_file,
            "-af", "volumedetect", "-f", "null", "-",
        ]
        output = self._run_ffmpeg_capture(cmd)
        if output:
            mean = self._parse_volumedetect(output, "mean_volume")
            peak = self._parse_volumedetect(output, "max_volume")
            return mean, peak

        return None, None

    def _check_silence(self, video_file: str) -> List[QAIssue]:
        """
        检测明显静音时段（silencedetect）

        Args:
            video_file: 视频文件路径

        Returns:
            静音问题列表（最多 10 条，避免噪音）
        """
        cmd = [
            self.config.ffmpeg_path, "-hide_banner", "-nostats", "-i", video_file,
            "-af", (
                f"silencedetect=noise={self.config.silence_threshold_db}dB:"
                f"d={self.config.min_silence_duration}"
            ),
            "-f", "null", "-",
        ]
        output = self._run_ffmpeg_capture(cmd)
        if not output:
            return []

        starts = [float(x) for x in re.findall(r"silence_start:\s*(-?\d+(?:\.\d+)?)", output)]
        ends = [float(x) for x in re.findall(r"silence_end:\s*(-?\d+(?:\.\d+)?)", output)]

        issues: List[QAIssue] = []
        for i, start in enumerate(starts):
            end = ends[i] if i < len(ends) else start + self.config.min_silence_duration
            duration = end - start
            if duration >= self.config.min_silence_duration:
                issues.append(QAIssue(
                    category=QAIssueCategory.TECHNICAL,
                    severity=QAIssueSeverity.MEDIUM,
                    title="检测到明显静音时段",
                    description=f"在 {start:.1f}s - {end:.1f}s 存在 {duration:.1f}s 的静音",
                    timestamp=start,
                    duration=duration,
                    suggestion="检查该时段音频是否正常生成"
                ))

        return issues[:10]

    def _check_missing_duplicate_dialogue(self, dialogues: List[Dict]) -> Tuple[float, List[QAIssue]]:
        """
        漏台词/重复台词检测（对照 Dialogue Timeline）

        - 漏台词：对白缺少文本（未翻译/未合成）
        - 重复台词：相同文本且起始时间间隔小于容差（重复切分/重复合成）

        Returns:
            (评分, 问题列表)
        """
        issues: List[QAIssue] = []
        if not dialogues:
            return 100.0, issues

        # 漏台词：文本为空或缺失
        missing = [d for d in dialogues if not (d.get("text") or "").strip()]
        if missing:
            issues.append(QAIssue(
                category=QAIssueCategory.VOICE,
                severity=QAIssueSeverity.HIGH,
                title="发现漏台词",
                description=f"发现 {len(missing)} 条对白缺少文本（可能未翻译/未合成）",
                suggestion="检查翻译和语音合成输出"
            ))

        # 重复台词：相同文本且起始时间接近
        duplicates = []
        seen_text: Dict[str, List[float]] = {}
        for d in dialogues:
            text = (d.get("text") or "").strip()
            if not text:
                continue
            start = float(d.get("start_time") or 0.0)
            if any(abs(prev - start) <= self.config.duplicate_dialogue_gap for prev in seen_text.get(text, [])):
                duplicates.append(text)
            seen_text.setdefault(text, []).append(start)
        if duplicates:
            issues.append(QAIssue(
                category=QAIssueCategory.VOICE,
                severity=QAIssueSeverity.MEDIUM,
                title="发现重复台词",
                description=f"发现 {len(duplicates)} 处重复台词（相同文本、时间重叠）",
                suggestion="检查字幕/对白切分是否重复"
            ))

        total = len(missing) + len(duplicates)
        score = 100.0 - (total / max(len(dialogues), 1)) * 40.0
        return max(score, 0.0), issues

    def _check_character_mismatch(self, dialogues: List[Dict], character_db: Optional[str]) -> Tuple[float, List[QAIssue]]:
        """
        人物错配检测（说话人 vs 计划人物）

        对白同时携带 speaker_id（说话人识别）与 character_id（计划人物）时，
        二者不一致即为错配。缺少 speaker 信息时给出 INFO 提示但不惩罚。

        Returns:
            (评分, 问题列表)
        """
        issues: List[QAIssue] = []
        if not dialogues:
            return 100.0, issues

        # 加载人物数据库（用于显示人物名）
        characters = {}
        if character_db and os.path.exists(character_db):
            try:
                with open(character_db, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    characters = data.get("characters", {})
            except Exception as e:
                logger.warning(f"加载人物数据库失败: {e}")

        mismatches = []
        checkable = 0
        for d in dialogues:
            character_id = d.get("character_id")
            speaker_id = d.get("speaker_id") or d.get("speaker")
            if not character_id or not speaker_id:
                continue
            checkable += 1
            if str(character_id) != str(speaker_id):
                char_name = characters.get(str(character_id), {}).get("name", character_id)
                mismatches.append((char_name, speaker_id, d.get("start_time", 0)))

        if checkable == 0:
            issues.append(QAIssue(
                category=QAIssueCategory.VOICE,
                severity=QAIssueSeverity.INFO,
                title="缺少说话人信息",
                description="对白时间轴缺少 speaker_id，无法执行人物错配检查",
                suggestion="为对白时间轴补充说话人识别结果"
            ))
            return 100.0, issues

        if mismatches:
            issues.append(QAIssue(
                category=QAIssueCategory.VOICE,
                severity=QAIssueSeverity.HIGH,
                title="人物错配",
                description=f"发现 {len(mismatches)} 处对白的人物与说话人不匹配，例如 {mismatches[0][0]} 被识别为 {mismatches[0][1]}",
                suggestion="检查说话人识别与人物映射结果"
            ))

        score = 100.0 - (len(mismatches) / checkable) * 100.0
        return max(score, 0.0), issues

    def _write_report(self, result: QAResult) -> Optional[str]:
        """
        写出 QA 报告文件（JSON）

        Args:
            result: QA 检查结果

        Returns:
            报告文件路径，未启用或失败时返回 None
        """
        if not self.config.report_enabled:
            return None
        try:
            os.makedirs(self.config.output_dir, exist_ok=True)
            base = Path(result.video_file).stem
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = Path(self.config.output_dir) / f"qa_report_{base}_{ts}.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(result.model_dump(), f, ensure_ascii=False, indent=2, default=str)
            return str(report_path)
        except Exception as e:
            logger.error(f"写出 QA 报告失败: {e}")
            return None

    def _check_voice_consistency(self, dialogues: List[Dict], character_db: Optional[str]) -> tuple[float, List[QAIssue]]:
        """
        检查音色一致性

        Args:
            dialogues: 对白列表
            character_db: 人物数据库路径

        Returns:
            (评分, 问题列表)
        """
        issues: List[QAIssue] = []

        if not dialogues:
            return 100.0, issues

        # 加载人物数据库
        characters = {}
        if character_db and os.path.exists(character_db):
            try:
                with open(character_db, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    characters = data.get("characters", {})
            except Exception as e:
                logger.warning(f"加载人物数据库失败: {e}")

        # 检查同一人物的音色是否一致
        character_voices: Dict[str, set] = {}
        for dialogue in dialogues:
            character_id = dialogue.get("character_id")
            voice_id = dialogue.get("voice_id")

            if character_id and voice_id:
                if character_id not in character_voices:
                    character_voices[character_id] = set()
                character_voices[character_id].add(voice_id)

        # 检查音色不一致的问题
        for character_id, voice_ids in character_voices.items():
            if len(voice_ids) > 1:
                character_name = characters.get(character_id, {}).get("name", character_id)
                issues.append(QAIssue(
                    category=QAIssueCategory.VOICE,
                    severity=QAIssueSeverity.HIGH,
                    title=f"人物音色不一致: {character_name}",
                    description=f"人物 {character_name} 使用了 {len(voice_ids)} 个不同的音色: {', '.join(voice_ids)}",
                    suggestion="统一人物的音色配置"
                ))

        # 计算评分
        if not character_voices:
            return 100.0, issues

        consistent_count = sum(1 for voices in character_voices.values() if len(voices) == 1)
        score = (consistent_count / len(character_voices)) * 100

        return score, issues

    def _check_emotion_match(self, dialogues: List[Dict]) -> tuple[float, List[QAIssue]]:
        """
        检查情绪匹配

        Args:
            dialogues: 对白列表

        Returns:
            (评分, 问题列表)
        """
        issues: List[QAIssue] = []

        if not dialogues:
            return 100.0, issues

        # 检查是否有情绪标签
        dialogues_with_emotion = [d for d in dialogues if d.get("emotion")]

        if not dialogues_with_emotion:
            issues.append(QAIssue(
                category=QAIssueCategory.VOICE,
                severity=QAIssueSeverity.MEDIUM,
                title="缺少情绪标签",
                description="对白缺少情绪标签，无法验证情绪匹配",
                suggestion="为对白添加情绪标签（如 neutral, happy, sad, angry, etc.）"
            ))
            return 50.0, issues

        # 检查情绪标签的合理性
        valid_emotions = {"neutral", "happy", "sad", "angry", "fearful", "disgusted", "surprised"}
        invalid_count = 0

        for dialogue in dialogues_with_emotion:
            emotion = dialogue.get("emotion", "").lower()
            if emotion not in valid_emotions:
                invalid_count += 1

        if invalid_count > 0:
            issues.append(QAIssue(
                category=QAIssueCategory.VOICE,
                severity=QAIssueSeverity.LOW,
                title="情绪标签不标准",
                description=f"发现 {invalid_count} 个非标准情绪标签",
                suggestion="使用标准情绪标签"
            ))

        # 计算评分
        score = 100.0 - (invalid_count / len(dialogues_with_emotion)) * 30

        return max(score, 0.0), issues

    def _check_speech_rate(self, dialogues: List[Dict]) -> tuple[float, List[QAIssue]]:
        """
        检查语速合理性

        Args:
            dialogues: 对白列表

        Returns:
            (评分, 问题列表)
        """
        issues: List[QAIssue] = []

        if not dialogues:
            return 100.0, issues

        # 计算每句对白的语速（字符/秒）
        unreasonable_count = 0

        for dialogue in dialogues:
            text = dialogue.get("text", "")
            start = dialogue.get("start_time", 0)
            end = dialogue.get("end_time", 0)

            if end > start and text:
                duration = end - start
                # 计算字符数（中文）
                char_count = len(text.strip())
                rate = char_count / duration  # 字符/秒

                # 中文正常语速约 3-5 字符/秒
                if rate < 1.0:
                    issues.append(QAIssue(
                        category=QAIssueCategory.VOICE,
                        severity=QAIssueSeverity.LOW,
                        title="语速过慢",
                        description=f"对白语速 {rate:.1f} 字符/秒 过慢",
                        details=f"文本: {text[:50]}...",
                        suggestion="调整语速或检查文本长度"
                    ))
                    unreasonable_count += 1
                elif rate > 8.0:
                    issues.append(QAIssue(
                        category=QAIssueCategory.VOICE,
                        severity=QAIssueSeverity.MEDIUM,
                        title="语速过快",
                        description=f"对白语速 {rate:.1f} 字符/秒 过快",
                        details=f"文本: {text[:50]}...",
                        suggestion="调整语速或增加停顿"
                    ))
                    unreasonable_count += 1

        # 计算评分
        score = 100.0 - (unreasonable_count / len(dialogues)) * 50

        return max(score, 0.0), issues

    def _check_translation_quality(self, dialogues: List[Dict]) -> tuple[float, List[QAIssue]]:
        """
        检查翻译质量（基础检查）

        Args:
            dialogues: 对白列表

        Returns:
            (评分, 问题列表)
        """
        issues: List[QAIssue] = []

        if not dialogues:
            return 100.0, issues

        # 基础检查：空文本、过短文本、过长文本
        empty_count = 0
        too_short_count = 0
        too_long_count = 0

        for dialogue in dialogues:
            text = dialogue.get("text", "").strip()

            if not text:
                empty_count += 1
            elif len(text) < 2:
                too_short_count += 1
            elif len(text) > 200:
                too_long_count += 1

        if empty_count > 0:
            issues.append(QAIssue(
                category=QAIssueCategory.VOICE,
                severity=QAIssueSeverity.HIGH,
                title="发现空文本",
                description=f"发现 {empty_count} 条空对白",
                suggestion="检查翻译输出"
            ))

        if too_short_count > 0:
            issues.append(QAIssue(
                category=QAIssueCategory.VOICE,
                severity=QAIssueSeverity.LOW,
                title="发现过短文本",
                description=f"发现 {too_short_count} 条过短对白（<2字符）"
            ))

        if too_long_count > 0:
            issues.append(QAIssue(
                category=QAIssueCategory.VOICE,
                severity=QAIssueSeverity.MEDIUM,
                title="发现过长文本",
                description=f"发现 {too_long_count} 条过长对白（>200字符）",
                suggestion="考虑分句"
            ))

        # 计算评分
        total_issues = empty_count * 3 + too_short_count + too_long_count * 2
        score = 100.0 - (total_issues / len(dialogues)) * 20

        return max(score, 0.0), issues

    def _calculate_technical_score(self, issues: List[QAIssue], video_info: Dict) -> float:
        """计算技术质量评分"""
        if not video_info:
            return 0.0

        # 基础分 100
        score = 100.0

        # 根据问题严重程度扣分
        for issue in issues:
            if issue.severity == QAIssueSeverity.CRITICAL:
                score -= 30
            elif issue.severity == QAIssueSeverity.HIGH:
                score -= 15
            elif issue.severity == QAIssueSeverity.MEDIUM:
                score -= 5
            elif issue.severity == QAIssueSeverity.LOW:
                score -= 2

        return max(score, 0.0)

    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 检查 FFprobe 是否可用
            result = subprocess.run(
                [self.config.ffprobe_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def close(self):
        """关闭 QA 检查器"""
        logger.info("关闭 QAChecker")
