"""
音频特征提取模块

使用 librosa 提取音频特征
"""
import numpy as np
from typing import List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

from .models import SpeakerSegment, AudioFeatures
from .config import M05Config


class AudioFeatureExtractor:
    """音频特征提取器"""

    def __init__(self, config: M05Config = None):
        """
        初始化提取器

        Args:
            config: M05 配置
        """
        self.config = config or M05Config()

    def extract(
        self,
        audio_path: str,
        segments: List[SpeakerSegment],
        sample_rate: int = None
    ) -> List[AudioFeatures]:
        """
        提取音频特征

        Args:
            audio_path: 音频文件路径
            segments: 说话人片段
            sample_rate: 采样率

        Returns:
            音频特征列表
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        import librosa

        sample_rate = sample_rate or self.config.sample_rate

        # 加载音频
        y, sr = librosa.load(audio_path, sr=sample_rate)

        features = []

        for segment in segments:
            # 提取片段
            start_sample = int(segment.start_time * sr)
            end_sample = int(segment.end_time * sr)

            segment_audio = y[start_sample:end_sample]

            # 跳过太短的片段
            if len(segment_audio) < sr * 0.1:
                continue

            # 提取特征
            try:
                feature = self._extract_segment_features(
                    segment_audio,
                    sr,
                    segment
                )

                if feature:
                    features.append(feature)

            except Exception as e:
                logger.warning(
                    f"Failed to extract features for segment "
                    f"{segment.speaker_id} ({segment.start_time}-{segment.end_time}): {e}"
                )
                continue

        logger.info(f"Extracted features for {len(features)} segments")

        return features

    def _extract_segment_features(
        self,
        audio: np.ndarray,
        sample_rate: int,
        segment: SpeakerSegment
    ) -> Optional[AudioFeatures]:
        """提取单个片段的特征"""
        # 音高特征
        pitch_mean, pitch_std, pitch_min, pitch_max = self._extract_pitch(
            audio, sample_rate
        )

        # 能量特征
        energy_mean, energy_std = self._extract_energy(audio)

        # 频谱特征
        spec_centroid_mean, spec_centroid_std = self._extract_spectral_centroid(
            audio, sample_rate
        )
        spec_rolloff_mean, spec_rolloff_std = self._extract_spectral_rolloff(
            audio, sample_rate
        )

        # MFCC 特征
        mfcc_mean, mfcc_std = self._extract_mfcc(audio, sample_rate)

        return AudioFeatures(
            speaker_id=segment.speaker_id,
            start_time=segment.start_time,
            end_time=segment.end_time,
            pitch_mean=pitch_mean,
            pitch_std=pitch_std,
            pitch_min=pitch_min,
            pitch_max=pitch_max,
            energy_mean=energy_mean,
            energy_std=energy_std,
            spectral_centroid_mean=spec_centroid_mean,
            spectral_centroid_std=spec_centroid_std,
            spectral_rolloff_mean=spec_rolloff_mean,
            spectral_rolloff_std=spec_rolloff_std,
            mfcc_mean=mfcc_mean.tolist(),
            mfcc_std=mfcc_std.tolist()
        )

    def _extract_pitch(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> tuple:
        """提取音高特征"""
        try:
            import librosa

            # 使用 pyin 算法提取音高
            pitches, voiced_flag, _ = librosa.pyin(
                audio,
                fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C7'),
                sr=sample_rate
            )

            # 过滤未 voiced 的部分
            voiced_pitches = pitches[voiced_flag]

            if len(voiced_pitches) == 0:
                return 0.0, 0.0, 0.0, 0.0

            pitch_mean = np.mean(voiced_pitches)
            pitch_std = np.std(voiced_pitches)
            pitch_min = np.min(voiced_pitches)
            pitch_max = np.max(voiced_pitches)

            return pitch_mean, pitch_std, pitch_min, pitch_max

        except Exception as e:
            logger.warning(f"Failed to extract pitch: {e}")
            return 0.0, 0.0, 0.0, 0.0

    def _extract_energy(self, audio: np.ndarray) -> tuple:
        """提取能量特征"""
        # 计算短时能量
        frame_length = self.config.n_fft
        hop_length = self.config.hop_length

        # 计算能量
        energy = np.array([
            np.sum(audio[i:i+frame_length]**2)
            for i in range(0, len(audio)-frame_length, hop_length)
        ])

        energy_mean = np.mean(energy)
        energy_std = np.std(energy)

        return energy_mean, energy_std

    def _extract_spectral_centroid(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> tuple:
        """提取频谱质心"""
        import librosa

        spec_centroids = librosa.feature.spectral_centroid(
            y=audio, sr=sample_rate, hop_length=self.config.hop_length
        )[0]

        spec_centroid_mean = np.mean(spec_centroids)
        spec_centroid_std = np.std(spec_centroids)

        return spec_centroid_mean, spec_centroid_std

    def _extract_spectral_rolloff(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> tuple:
        """提取频谱滚降"""
        import librosa

        spec_rolloffs = librosa.feature.spectral_rolloff(
            y=audio, sr=sample_rate, hop_length=self.config.hop_length
        )[0]

        spec_rolloff_mean = np.mean(spec_rolloffs)
        spec_rolloff_std = np.std(spec_rolloffs)

        return spec_rolloff_mean, spec_rolloff_std

    def _extract_mfcc(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> tuple:
        """提取 MFCC 特征"""
        import librosa

        mfccs = librosa.feature.mfcc(
            y=audio,
            sr=sample_rate,
            n_mfcc=self.config.n_mfcc,
            n_fft=self.config.n_fft,
            hop_length=self.config.hop_length
        )

        mfcc_mean = np.mean(mfccs, axis=1)
        mfcc_std = np.std(mfccs, axis=1)

        return mfcc_mean, mfcc_std
