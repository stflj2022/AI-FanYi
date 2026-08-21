"""
说话人分离模块

使用 pyannote.audio 进行说话人分离
"""
import numpy as np
from typing import List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

from .models import SpeakerSegment, DiarizationResult
from .config import M05Config


class SpeakerDiarization:
    """说话人分离器"""

    def __init__(self, config: M05Config = None):
        """
        初始化分离器

        Args:
            config: M05 配置
        """
        self.config = config or M05Config()

        # 检查 CUDA 可用性（torch 未安装时默认为 CPU）
        self.device = self._resolve_device()

        logger.info(f"Using device: {self.device}")

        # 加载模型
        self.model = None
        self._load_model()

    def _resolve_device(self) -> str:
        """解析运行设备，torch 不可用时回退到 CPU。"""
        try:
            import torch
            if torch.cuda.is_available() and self.config.device == "cuda":
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    def _load_model(self):
        """加载说话人分离模型"""
        try:
            from pyannote.audio import Pipeline

            logger.info(f"Loading diarization model: {self.config.diarization_model}")

            # 创建 Pipeline
            self.model = Pipeline.from_pretrained(
                self.config.diarization_model,
                use_auth_token=False  # TODO: 添加 HF token
            )

            # 移动到设备
            if self.device == "cuda":
                self.model.to(self.device)

            logger.info("Diarization model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load diarization model: {e}")
            self.model = None

    def diarize(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None
    ) -> DiarizationResult:
        """
        说话人分离

        Args:
            audio_path: 音频文件路径
            num_speakers: 说话人数量（可选）

        Returns:
            说话人分离结果
        """
        if not self.model:
            raise RuntimeError("Diarization model not loaded")

        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Starting diarization: {audio_path}")

        # 执行分离
        try:
            diarization = self.model(
                audio_path,
                num_speakers=num_speakers
            )

            # 转换为 SpeakerSegment 列表
            segments = self._convert_to_segments(diarization)

            # 计算说话人数量
            speaker_ids = set(s.speaker_id for s in segments)

            # 计算总时长
            total_duration = max(s.end_time for s in segments) if segments else 0.0

            result = DiarizationResult(
                segments=segments,
                num_speakers=len(speaker_ids),
                total_duration=total_duration
            )

            logger.info(
                f"Diarization completed: {len(segments)} segments, "
                f"{len(speaker_ids)} speakers"
            )

            return result

        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            raise

    def _convert_to_segments(
        self,
        diarization
    ) -> List[SpeakerSegment]:
        """
        将 pyannote 分离结果转换为 SpeakerSegment 列表

        Args:
            diarization: pyannote 分离结果

        Returns:
            SpeakerSegment 列表
        """
        segments = []

        for turn, _, speaker in diarization.itertracks(yield_label=True):
            # 计算置信度（简化版）
            confidence = 0.95  # pyannote 不直接提供置信度

            segment = SpeakerSegment(
                speaker_id=speaker,
                start_time=float(turn.start),
                end_time=float(turn.end),
                confidence=confidence
            )

            segments.append(segment)

        # 按时间排序
        segments.sort(key=lambda s: s.start_time)

        return segments

    def filter_short_segments(
        self,
        result: DiarizationResult,
        min_duration: float = None
    ) -> DiarizationResult:
        """
        过滤短片段

        Args:
            result: 分离结果
            min_duration: 最小时长（秒）

        Returns:
            过滤后的结果
        """
        min_duration = min_duration or self.config.min_speaker_duration

        filtered_segments = [
            s for s in result.segments
            if s.end_time - s.start_time >= min_duration
        ]

        # 计算新的说话人数量
        speaker_ids = set(s.speaker_id for s in filtered_segments)

        filtered_result = DiarizationResult(
            segments=filtered_segments,
            num_speakers=len(speaker_ids),
            total_duration=result.total_duration
        )

        logger.info(
            f"Filtered segments: {len(result.segments)} -> {len(filtered_segments)}"
        )

        return filtered_result
