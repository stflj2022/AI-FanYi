"""
TTS 引擎

语音合成引擎，支持音高变换和时间拉伸
"""
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from .config import M09Config
from .model_manager import TTSModelManager
from .models import AudioArtifact


class TTSEngine:
    """TTS 引擎"""

    def __init__(
        self,
        model_manager: TTSModelManager,
        config: M09Config = None
    ):
        """
        初始化引擎

        Args:
            model_manager: 模型管理器
            config: M09 配置
        """
        self.model_manager = model_manager
        self.config = config or M09Config()

    def synthesize(
        self,
        text: str,
        voice_profile_id: str,
        prosody: Dict[str, Any],
        output_path: str
    ) -> Optional[AudioArtifact]:
        """
        合成语音

        Args:
            text: 文本
            voice_profile_id: 音色 ID
            prosody: 韵律参数
            output_path: 输出路径

        Returns:
            音频 Artifact
        """
        if not self.model_manager.current_model:
            raise RuntimeError("No TTS model loaded")

        logger.info(f"Synthesizing: {text[:50]}...")

        try:
            # 1. 前处理文本
            processed_text = self._preprocess_text(text)

            # 2. 调用 TTS 模型
            audio = self._call_tts_model(
                processed_text,
                voice_profile_id,
                prosody
            )

            if audio is None:
                return None

            # 3. 应用韵律处理
            if self.config.enable_pitch_shift:
                audio = self._apply_pitch_shift(
                    audio,
                    prosody.get("pitch", 0.0)
                )

            if self.config.enable_time_stretch:
                audio = self._apply_time_stretch(
                    audio,
                    prosody.get("speed", 1.0)
                )

            # 4. 添加停顿
            audio = self._add_pauses(
                audio,
                prosody.get("pause_before", 0.0),
                prosody.get("pause_after", 0.0)
            )

            # 5. 后处理
            audio = self._postprocess_audio(audio, prosody)

            # 6. 保存音频
            self._save_audio(audio, output_path)

            # 7. 创建 Artifact
            duration = len(audio) / self.config.sample_rate

            artifact = AudioArtifact(
                artifact_id=f"audio_{Path(output_path).stem}",
                dialogue_id=prosody.get("dialogue_id", ""),
                character_id=prosody.get("character_id", ""),
                file_path=output_path,
                duration=duration,
                sample_rate=self.config.sample_rate
            )

            logger.info(f"Synthesis completed: {output_path} ({duration:.2f}s)")

            return artifact

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return None

    def _preprocess_text(self, text: str) -> str:
        """
        前处理文本

        Args:
            text: 原始文本

        Returns:
            处理后的文本
        """
        # 移除多余空格
        text = " ".join(text.split())

        # TODO: 添加更多前处理
        # - 标点符号规范化
        # - 数字转换
        # - 缩写展开

        return text

    def _call_tts_model(
        self,
        text: str,
        voice_profile_id: str,
        prosody: Dict[str, Any]
    ) -> Optional[np.ndarray]:
        """
        调用 TTS 模型

        Args:
            text: 文本
            voice_profile_id: 音色 ID
            prosody: 韵律参数

        Returns:
            音频数据
        """
        try:
            model = self.model_manager.current_model

            # 调用模型
            audio = model.inference(
                text=text,
                voice_profile_id=voice_profile_id,
                emotion=prosody.get("emotion", "neutral"),
                emotion_intensity=prosody.get("emotion_intensity", 0.5)
            )

            return audio

        except Exception as e:
            logger.error(f"TTS model inference failed: {e}")
            return None

    def _apply_pitch_shift(
        self,
        audio: np.ndarray,
        pitch_shift: float
    ) -> np.ndarray:
        """
        音高变换

        Args:
            audio: 音频数据
            pitch_shift: 音高偏移（st）

        Returns:
            处理后的音频
        """
        if pitch_shift == 0.0:
            return audio

        try:
            if self.config.pitch_shift_lib == "pyrubberband":
                return self._pitch_shift_rubberband(audio, pitch_shift)
            else:
                return self._pitch_shift_librosa(audio, pitch_shift)
        except Exception as e:
            logger.warning(f"Pitch shift failed: {e}, using original audio")
            return audio

    def _pitch_shift_rubberband(
        self,
        audio: np.ndarray,
        pitch_shift: float
    ) -> np.ndarray:
        """使用 pyrubberband 进行音高变换"""
        try:
            import pyrubberband as pyrb

            # 计算 pitch shift ratio
            # 1 semitone = 2^(1/12) ≈ 1.0595
            ratio = 2 ** (pitch_shift / 12.0)

            # 应用音高变换
            shifted = pyrb.pitch_shift(
                audio,
                self.config.sample_rate,
                ratio
            )

            return shifted

        except ImportError:
            logger.warning("pyrubberband not available, falling back to librosa")
            return self._pitch_shift_librosa(audio, pitch_shift)
        except Exception as e:
            logger.error(f"pyrubberband pitch shift failed: {e}")
            raise

    def _pitch_shift_librosa(
        self,
        audio: np.ndarray,
        pitch_shift: float
    ) -> np.ndarray:
        """使用 librosa 进行音高变换"""
        try:
            import librosa

            # 计算 pitch shift ratio
            ratio = 2 ** (pitch_shift / 12.0)

            # 应用音高变换
            shifted = librosa.effects.pitch_shift(
                audio,
                sr=self.config.sample_rate,
                n_steps=pitch_shift
            )

            return shifted

        except Exception as e:
            logger.error(f"librosa pitch shift failed: {e}")
            raise

    def _apply_time_stretch(
        self,
        audio: np.ndarray,
        speed_factor: float
    ) -> np.ndarray:
        """
        时间拉伸

        Args:
            audio: 音频数据
            speed_factor: 速度因子（>1 加速，<1 减速）

        Returns:
            处理后的音频
        """
        if speed_factor == 1.0:
            return audio

        try:
            import librosa

            # 应用时间拉伸
            stretched = librosa.effects.time_stretch(
                audio,
                rate=speed_factor
            )

            return stretched

        except Exception as e:
            logger.warning(f"Time stretch failed: {e}, using original audio")
            return audio

    def _add_pauses(
        self,
        audio: np.ndarray,
        pause_before: float,
        pause_after: float
    ) -> np.ndarray:
        """
        添加停顿

        Args:
            audio: 音频数据
            pause_before: 句前停顿（秒）
            pause_after: 句后停顿（秒）

        Returns:
            处理后的音频
        """
        if pause_before == 0.0 and pause_after == 0.0:
            return audio

        # 计算停顿样本数
        before_samples = int(pause_before * self.config.sample_rate)
        after_samples = int(pause_after * self.config.sample_rate)

        # 创建停顿（静音）
        silence_before = np.zeros(before_samples, dtype=audio.dtype)
        silence_after = np.zeros(after_samples, dtype=audio.dtype)

        # 拼接
        audio_with_pauses = np.concatenate([
            silence_before,
            audio,
            silence_after
        ])

        return audio_with_pauses

    def _postprocess_audio(
        self,
        audio: np.ndarray,
        prosody: Dict[str, Any]
    ) -> np.ndarray:
        """
        后处理音频

        Args:
            audio: 音频数据
            prosody: 韵律参数

        Returns:
            处理后的音频
        """
        # 归一化
        audio = audio / (np.max(np.abs(audio)) + 1e-8)

        # 应用能量调整
        energy = prosody.get("energy", 1.0)
        audio = audio * energy

        # 限制范围
        audio = np.clip(audio, -1.0, 1.0)

        return audio

    def _save_audio(self, audio: np.ndarray, output_path: str):
        """
        保存音频

        Args:
            audio: 音频数据
            output_path: 输出路径
        """
        # 确保目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # 保存
        sf.write(
            output_path,
            audio,
            self.config.sample_rate
        )
