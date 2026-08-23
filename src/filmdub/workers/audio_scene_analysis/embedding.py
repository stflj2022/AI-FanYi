"""
说话人嵌入提取模块

使用 speechbrain ECAPA-TDNN 提取说话人嵌入
"""
from __future__ import annotations

import numpy as np
from typing import List, Dict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

from .models import SpeakerSegment, SpeakerEmbedding
from .config import M05Config


class SpeakerEmbeddingExtractor:
    """说话人嵌入提取器"""

    def __init__(self, config: M05Config = None):
        """
        初始化提取器

        Args:
            config: M05 配置
        """
        self.config = config or M05Config()

        # 检查 CUDA 可用性（torch 未安装时默认为 CPU）
        self.device = self._resolve_device()

        logger.info(f"Using device: {self.device}")

        # 加载模型
        self.model = None
        self.processor = None
        self._load_model()

    def _resolve_device(self) -> str:
        """解析运行设备，torch 不可用时回退到 CPU。"""
        try:
            # 使用 subprocess 隔离导入 torch，避免与 aiosqlite 冲突
            import subprocess
            import sys
            result = subprocess.run(
                [sys.executable, "-c", "import torch; print(torch.cuda.is_available())"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip() == "True":
                if self.config.device == "cuda":
                    return "cuda"
        except Exception:
            pass
        return "cpu"

    def _load_model(self):
        """加载嵌入提取模型"""
        try:
            from speechbrain.inference.speaker import SpeakerRecognition

            logger.info(f"Loading embedding model: {self.config.embedding_model}")

            # 创建模型
            self.model = SpeakerRecognition.from_hparams(
                source=self.config.embedding_model,
                run_opts={"device": str(self.device)}
            )

            logger.info("Embedding model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.model = None

    def extract(
        self,
        audio_path: str,
        segments: List[SpeakerSegment],
        sample_rate: int = None
    ) -> List[SpeakerEmbedding]:
        """
        提取说话人嵌入

        Args:
            audio_path: 音频文件路径
            segments: 说话人片段
            sample_rate: 采样率

        Returns:
            说话人嵌入列表
        """
        if not self.model:
            raise RuntimeError("Embedding model not loaded")

        sample_rate = sample_rate or self.config.sample_rate

        # 加载音频
        waveform = self._load_audio(audio_path, sample_rate)

        # 按说话人分组
        speaker_segments = self._group_by_speaker(segments)

        # 提取嵌入
        embeddings = []

        for speaker_id, segs in speaker_segments.items():
            # 拼接片段
            concatenated_waveform = self._concatenate_segments(
                waveform,
                segs,
                sample_rate
            )

            # 提取嵌入
            embedding = self._extract_embedding(concatenated_waveform)

            if embedding is not None:
                speaker_embedding = SpeakerEmbedding(
                    speaker_id=speaker_id,
                    start_time=min(s.start_time for s in segs),
                    end_time=max(s.end_time for s in segs),
                    embedding=embedding.tolist(),
                    confidence=0.95,  # ECAPA-TDNN 通常置信度较高
                    segment_count=len(segs)
                )

                embeddings.append(speaker_embedding)

                logger.info(
                    f"Extracted embedding for speaker {speaker_id}: "
                    f"{len(segs)} segments"
                )

        return embeddings

    def _load_audio(self, audio_path: str, sample_rate: int) -> torch.Tensor:
        """加载音频文件"""
        try:
            import torch
            from torchaudio import load

            waveform, sr = load(audio_path)

            # 重采样
            if sr != sample_rate:
                from torchaudio.transforms import Resample
                resampler = Resample(sr, sample_rate)
                waveform = resampler(waveform)

            # 转换为单声道
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)

            return waveform.to(self.device)

        except Exception as e:
            logger.error(f"Failed to load audio: {e}")
            raise

    def _group_by_speaker(
        self,
        segments: List[SpeakerSegment]
    ) -> Dict[str, List[SpeakerSegment]]:
        """按说话人分组"""
        speaker_segments = {}

        for segment in segments:
            if segment.speaker_id not in speaker_segments:
                speaker_segments[segment.speaker_id] = []

            speaker_segments[segment.speaker_id].append(segment)

        return speaker_segments

    def _concatenate_segments(
        self,
        waveform: torch.Tensor,
        segments: List[SpeakerSegment],
        sample_rate: int
    ) -> torch.Tensor:
        """拼接音频片段"""
        import torch

        segments_waveforms = []

        for segment in segments:
            start_sample = int(segment.start_time * sample_rate)
            end_sample = int(segment.end_time * sample_rate)

            segment_waveform = waveform[:, start_sample:end_sample]
            segments_waveforms.append(segment_waveform)

        # 拼接
        concatenated = torch.cat(segments_waveforms, dim=1)

        return concatenated

    def _extract_embedding(self, waveform: torch.Tensor) -> np.ndarray:
        """提取嵌入"""
        try:
            import torch

            with torch.no_grad():
                # ECAPA-TDNN 期望形状: (batch, time)
                if waveform.dim() == 1:
                    waveform = waveform.unsqueeze(0)
                elif waveform.dim() == 2 and waveform.shape[0] == 1:
                    pass  # 已经是正确形状
                elif waveform.dim() == 2 and waveform.shape[1] == 1:
                    waveform = waveform.t()
                else:
                    waveform = waveform.mean(dim=0, keepdim=True)

                # 提取嵌入
                embedding = self.model.encode_batch(waveform)

                # 归一化
                embedding = embedding / torch.norm(embedding, dim=1, keepdim=True)

                # 转换为 numpy
                return embedding.squeeze(0).cpu().numpy()

        except Exception as e:
            logger.error(f"Failed to extract embedding: {e}")
            return None
