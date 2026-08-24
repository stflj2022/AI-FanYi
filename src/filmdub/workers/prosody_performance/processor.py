"""
M10 Prosody Processor - 音频韵律处理器

使用 FFmpeg 进行音频处理：
- 音高变换
- 时间拉伸（语速调整）
- 音量调整
- 停顿处理
- 呼吸声添加
"""

import asyncio
import logging
import random
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import tempfile

import numpy as np

from .config import M10Config
from .models import ProsodyParams, EmotionType

logger = logging.getLogger(__name__)


class ProsodyProcessor:
    """韵律处理器"""

    def __init__(self, config: M10Config = None):
        """
        初始化处理器

        Args:
            config: M10 配置
        """
        self.config = config or M10Config()

    async def process_audio(
        self,
        input_path: Path,
        output_path: Path,
        params: ProsodyParams,
    ) -> Tuple[bool, Optional[float], Optional[str]]:
        """
        处理音频

        Args:
            input_path: 输入音频路径
            output_path: 输出音频路径
            params: 韵律参数

        Returns:
            (success, duration, error_message)
        """
        try:
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 获取原始时长
            original_duration = await self._get_audio_duration(input_path)

            # 应用音量调整
            temp_volume = None
            if params.volume != 1.0:
                temp_volume = self._get_temp_path(".wav")
                await self._adjust_volume(input_path, temp_volume, params.volume)
                input_path = temp_volume

            # 应用语速调整（使用 atempo）
            temp_speed = None
            if params.speed != 1.0:
                temp_speed = self._get_temp_path(".wav")
                await self._adjust_speed(input_path, temp_speed, params.speed)
                input_path = temp_speed

            # 应用音高变换（使用 rubberband 或 aresample）
            # 注意：FFmpeg 原生音高变换有限，这里使用简单的重采样
            temp_pitch = None
            if params.pitch != 1.0:
                temp_pitch = self._get_temp_path(".wav")
                await self._adjust_pitch(input_path, temp_pitch, params.pitch)
                input_path = temp_pitch

            # 添加停顿
            final_output = output_path
            if params.pause_before > 0 or params.pause_after > 0:
                await self._add_pauses(input_path, output_path, params.pause_before, params.pause_after)
            else:
                # 直接复制最终文件
                import shutil
                shutil.copy(input_path, output_path)

            # 获取处理后时长
            final_duration = await self._get_audio_duration(output_path)

            # 清理临时文件
            for temp_file in [temp_volume, temp_speed, temp_pitch]:
                if temp_file and temp_file.exists():
                    temp_file.unlink()

            return True, final_duration, None

        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            return False, None, str(e)

    async def _get_audio_duration(self, audio_path: Path) -> float:
        """获取音频时长（秒）"""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ]
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {stderr.decode()}")
        return float(stdout.decode().strip())

    async def _adjust_volume(self, input_path: Path, output_path: Path, volume: float):
        """调整音量"""
        # 转换为 dB：volume 1.0 = 0dB
        db = 20 * np.log10(volume)
        cmd = [
            "ffmpeg",
            "-y",  # 覆盖输出文件
            "-i", str(input_path),
            "-af", f"volume={db}dB",
            "-c:a", "pcm_s16le",  # 输出为 PCM
            str(output_path)
        ]
        await self._run_ffmpeg(cmd)

    async def _adjust_speed(self, input_path: Path, output_path: Path, speed: float):
        """
        调整语速

        注意：FFmpeg 的 atempo 只能在 0.5-2.0 范围内，
        如果超出范围，需要链式调用多个 atempo
        """
        # 限制在有效范围内
        speed = self.config.clamp_speed(speed)

        # 构建滤波器链
        if 0.5 <= speed <= 2.0:
            filter_str = f"atempo={speed}"
        else:
            # 链式调用多个 atempo
            filters = []
            remaining = speed
            while remaining > 2.0:
                filters.append("atempo=2.0")
                remaining /= 2.0
            while remaining < 0.5:
                filters.append("atempo=0.5")
                remaining /= 0.5
            filters.append(f"atempo={remaining}")
            filter_str = ",".join(filters)

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-af", filter_str,
            "-c:a", "pcm_s16le",
            str(output_path)
        ]
        await self._run_ffmpeg(cmd)

    async def _adjust_pitch(self, input_path: Path, output_path: Path, pitch: float):
        """
        调整音高

        使用重采样实现简单的音高变换
        注意：这会同时改变语速，仅作为简化实现
        """
        pitch = self.config.clamp_pitch(pitch)

        # 限制在合理范围内以避免质量问题
        if 0.8 <= pitch <= 1.25:
            # 使用 aresample 进行重采样
            new_sample_rate = int(self.config.sample_rate * pitch)
            cmd = [
                "ffmpeg",
                "-y",
                "-i", str(input_path),
                "-af", f"aresample={new_sample_rate},aresample={self.config.sample_rate}",
                "-c:a", "pcm_s16le",
                str(output_path)
            ]
        else:
            # 超出范围，不处理或复制
            import shutil
            shutil.copy(input_path, output_path)
            return

        await self._run_ffmpeg(cmd)

    async def _add_pauses(
        self,
        input_path: Path,
        output_path: Path,
        pause_before: float,
        pause_after: float
    ):
        """添加停顿（静音）"""
        filter_parts = []

        # 前停顿
        if pause_before > 0:
            filter_parts.append(f"adelay={int(pause_before * 1000)}|{int(pause_before * 1000)}")

        # 后停顿（使用 apad）
        if pause_after > 0:
            filter_parts.append(f"apad=whole_dur={pause_after}")

        if not filter_parts:
            import shutil
            shutil.copy(input_path, output_path)
            return

        filter_str = ",".join(filter_parts)
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-af", filter_str,
            "-c:a", "pcm_s16le",
            str(output_path)
        ]
        await self._run_ffmpeg(cmd)

    async def _add_breath(self, audio_path: Path) -> Path:
        """
        添加呼吸声（简化实现）

        实际实现应该使用真实的呼吸声样本
        这里只做占位
        """
        # TODO: 实现真实的呼吸声添加
        return audio_path

    def map_emotion_to_prosody(self, emotion: EmotionType) -> ProsodyParams:
        """
        将情绪映射到韵律参数

        Args:
            emotion: 情绪类型

        Returns:
            韵律参数
        """
        params_dict = self.config.get_emotion_params(emotion.value)

        # 随机添加一些变化，使声音更自然
        variation = 0.05  # 5% 变化
        pitch = params_dict["pitch"] * random.uniform(1 - variation, 1 + variation)
        speed = params_dict["speed"] * random.uniform(1 - variation, 1 + variation)
        volume = params_dict["volume"] * random.uniform(1 - variation, 1 + variation)

        # 随机添加呼吸声
        breath = random.random() < self.config.breath_probability

        return ProsodyParams(
            pitch=self.config.clamp_pitch(pitch),
            speed=self.config.clamp_speed(speed),
            volume=self.config.clamp_volume(volume),
            pause_before=random.uniform(0, self.config.default_pause * 0.3),
            pause_after=random.uniform(0, self.config.default_pause * 0.5),
            breath=breath,
        )

    async def align_duration(
        self,
        audio_path: Path,
        target_duration: float,
        current_duration: float,
    ) -> float:
        """
        调整音频时长以匹配目标时长

        Args:
            audio_path: 音频路径
            target_duration: 目标时长
            current_duration: 当前时长

        Returns:
            实际调整的语速因子
        """
        if target_duration is None or current_duration is None:
            return 1.0

        if current_duration == 0:
            return 1.0

        speed = current_duration / target_duration
        speed = self.config.clamp_speed(speed)
        return speed

    async def _run_ffmpeg(self, cmd: list):
        """运行 FFmpeg 命令"""
        logger.debug(f"Running FFmpeg: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"FFmpeg failed: {error_msg}")

        logger.debug(f"FFmpeg completed successfully")

    def _get_temp_path(self, suffix: str = ".wav") -> Path:
        """获取临时文件路径"""
        return Path(tempfile.gettempdir()) / f"prosody_{random.randint(10000, 99999)}{suffix}"
