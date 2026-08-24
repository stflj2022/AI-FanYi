"""
高级音频混合器

支持：
- 音频分离（原声/背景/环境音）
- 多音轨混合
- LUFS 响度归一化
- 原声静音/衰减
"""
import asyncio
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from .config import M11Config
from .models import AudioSegment, AudioTrack, AudioTrackType

logger = logging.getLogger(__name__)


class AdvancedAudioMixer:
    """高级音频混合器"""

    def __init__(self, config: M11Config = None):
        """
        初始化混合器

        Args:
            config: M11 配置
        """
        self.config = config or M11Config()

    async def separate_audio(
        self,
        original_audio_path: Path,
        output_dir: Path,
    ) -> Dict[str, Path]:
        """
        分离音频为多个音轨

        Args:
            original_audio_path: 原始音频路径
            output_dir: 输出目录

        Returns:
            分离后的音轨路径映射
        """
        if not self.config.enable_audio_separation:
            logger.info("Audio separation disabled, returning original as single track")
            return {
                "vocals": original_audio_path,
                "drums": original_audio_path,
                "bass": original_audio_path,
                "other": original_audio_path,
            }

        logger.info(f"Separating audio: {original_audio_path}")

        try:
            # 导入分离适配器
            from filmdub.adapter import AudioSeparationAdapter

            adapter = AudioSeparationAdapter(
                model=self.config.separation_model,
                device=self.config.separation_device,
            )

            # 分离音频
            stems = await adapter.separate(
                audio_path=original_audio_path,
                output_dir=output_dir,
                stems=["vocals", "drums", "bass", "other"]
            )

            logger.info(f"Audio separated into {len(stems)} stems")

            return stems

        except Exception as e:
            logger.warning(f"Audio separation failed: {e}, using original as fallback")
            return {
                "vocals": original_audio_path,
                "drums": original_audio_path,
                "bass": original_audio_path,
                "other": original_audio_path,
            }

    async def normalize_lufs(
        self,
        input_path: Path,
        output_path: Path,
        target_lufs: Optional[float] = None,
    ) -> bool:
        """
        LUFS 响度归一化

        Args:
            input_path: 输入音频路径
            output_path: 输出音频路径
            target_lufs: 目标 LUFS 值

        Returns:
            是否成功
        """
        if not self.config.enable_lufs_normalization:
            # 直接复制
            import shutil
            shutil.copy(input_path, output_path)
            return True

        target_lufs = target_lufs or self.config.target_lufs

        logger.info(f"Normalizing LUFS to {target_lufs}: {input_path}")

        try:
            # 使用 FFmpeg 的 loudnorm 滤镜
            cmd = [
                self.config.ffmpeg_path,
                "-y",
                "-i", str(input_path),
                "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
                "-c:a", "pcm_s16le",
                str(output_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.warning(f"LUFS normalization failed: {stderr.decode()}")
                # Fallback: 直接复制
                import shutil
                shutil.copy(input_path, output_path)
                return False

            logger.info(f"LUFS normalized: {output_path}")
            return True

        except Exception as e:
            logger.warning(f"LUFS normalization exception: {e}")
            # Fallback
            import shutil
            shutil.copy(input_path, output_path)
            return False

    async def suppress_original_vocals(
        self,
        vocals_path: Path,
        dialogue_segments: List[AudioSegment],
        output_path: Path,
    ) -> Path:
        """
        在对白时段静音/衰减原人声

        Args:
            vocals_path: 原人声音频路径
            dialogue_segments: 对白片段列表
            output_path: 输出路径

        Returns:
            处理后的音频路径
        """
        if self.config.original_vocal_volume >= 1.0:
            # 不需要处理
            import shutil
            shutil.copy(vocals_path, output_path)
            return output_path

        logger.info(f"Suppressing original vocals in {len(dialogue_segments)} dialogue segments")

        try:
            # 构建音量调节滤镜
            # 使用 volume 滤镜 + adelay 实现分段音量控制

            filter_parts = []

            # 基础音量（非对白时段）
            base_volume = self.config.original_vocal_volume
            if base_volume != 1.0:
                db = 20 * (2.0 if base_volume == 0 else base_volume).__class__.__bases__[0].__bases__
                # 简化：使用 adelay + volume 滤镜链
                pass

            # 更复杂的实现需要使用分段处理
            # 这里使用简化方案：整体降低音量
            if base_volume < 1.0:
                db = 20 * (base_volume if base_volume > 0 else 0.0001).log10()
                filter_parts.append(f"volume={db}dB")

            if filter_parts:
                filter_str = ",".join(filter_parts)
                cmd = [
                    self.config.ffmpeg_path,
                    "-y",
                    "-i", str(vocals_path),
                    "-af", filter_str,
                    "-c:a", "pcm_s16le",
                    str(output_path),
                ]

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    logger.warning(f"Vocal suppression failed: {stderr.decode()}")
                    import shutil
                    shutil.copy(vocals_path, output_path)
            else:
                import shutil
                shutil.copy(vocals_path, output_path)

            logger.info(f"Original vocals suppressed: {output_path}")
            return output_path

        except Exception as e:
            logger.warning(f"Vocal suppression exception: {e}")
            import shutil
            shutil.copy(vocals_path, output_path)
            return output_path

    async def mix_tracks(
        self,
        dialogue_segments: List[AudioSegment],
        background_tracks: List[AudioTrack],
        ambient_tracks: List[AudioTrack],
        effects_tracks: List[AudioTrack],
        original_vocals: Optional[Path] = None,
        output_path: Path = None,
        total_duration: float = 0.0,
    ) -> Path:
        """
        混合所有音轨

        Args:
            dialogue_segments: AI 对白片段列表
            background_tracks: 背景音乐轨道
            ambient_tracks: 环境音轨道
            effects_tracks: 音效轨道
            original_vocals: 处理后的原人声（可选）
            output_path: 输出路径
            total_duration: 总时长

        Returns:
            混合后的音频路径
        """
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".wav"))

        logger.info(f"Mixing audio tracks: {len(dialogue_segments)} dialogues, "
                    f"{len(background_tracks)} background, {len(ambient_tracks)} ambient, "
                    f"{len(effects_tracks)} effects")

        # 构建 FFmpeg 命令
        cmd = [self.config.ffmpeg_path, "-y"]

        # 输入文件
        inputs = []
        input_labels = []

        # 1. 静音底床（保证输出时长）
        inputs.extend(["-f", "lavfi", "-t", str(max(1.0, total_duration)),
                       "-i", f"anullsrc=r={self.config.audio_sample_rate}:cl=stereo"])
        input_labels.append("[0a]")

        # 2. AI 对白片段
        for i, segment in enumerate(dialogue_segments):
            inputs.extend(["-i", str(segment.audio_path)])
            input_labels.append(f"[{len(input_labels)}a]")

        # 3. 背景音乐
        for track in background_tracks:
            inputs.extend(["-i", str(track.audio_path)])
            input_labels.append(f"[{len(input_labels)}a]")

        # 4. 环境音
        for track in ambient_tracks:
            inputs.extend(["-i", str(track.audio_path)])
            input_labels.append(f"[{len(input_labels)}a]")

        # 5. 音效
        for track in effects_tracks:
            inputs.extend(["-i", str(track.audio_path)])
            input_labels.append(f"[{len(input_labels)}a]")

        # 6. 原人声（可选）
        if original_vocals:
            inputs.extend(["-i", str(original_vocals)])
            input_labels.append(f"[{len(input_labels)}a]")

        cmd.extend(inputs)

        # 构建滤镜链
        filter_complex = []

        # 处理对白片段（添加延迟、音量）
        dialogue_idx = 1  # 从索引 1 开始（0 是静音底床）
        for i, segment in enumerate(dialogue_segments):
            label = input_labels[dialogue_idx + i]
            delayed = f"[d{i}a]"

            # 延迟
            delay = segment.target_start_time
            filter_complex.append(f"{label}adelay={int(delay * 1000)}|{int(delay * 1000)}{delayed}")

        # 处理背景音乐（音量、淡入淡出）
        bg_idx = dialogue_idx + len(dialogue_segments)
        for i, track in enumerate(background_tracks):
            label = input_labels[bg_idx + i]
            processed = f"[bg{i}a]"

            filters = []
            if track.volume != 1.0:
                db = 20 * (track.volume if track.volume > 0 else 0.0001).log10()
                filters.append(f"volume={db}dB")
            if track.fade_in > 0:
                filters.append(f"afade=t=in:st=0:d={track.fade_in}")
            if track.fade_out > 0:
                filters.append(f"afade=t=out:st={max(0, (track.end_time or total_duration) - track.fade_out)}:d={track.fade_out}")

            if filters:
                filter_complex.append(f"{label}{','.join(filters)}{processed}")
            else:
                filter_complex.append(f"{label}{processed}")

        # 处理环境音
        amb_idx = bg_idx + len(background_tracks)
        for i, track in enumerate(ambient_tracks):
            label = input_labels[amb_idx + i]
            processed = f"[amb{i}a]"

            filters = []
            if track.volume != self.config.ambient_volume:
                db = 20 * (track.volume if track.volume > 0 else 0.0001).log10()
                filters.append(f"volume={db}dB")

            if filters:
                filter_complex.append(f"{label}{','.join(filters)}{processed}")
            else:
                filter_complex.append(f"{label}{processed}")

        # 处理音效
        eff_idx = amb_idx + len(ambient_tracks)
        for i, track in enumerate(effects_tracks):
            label = input_labels[eff_idx + i]
            processed = f"[eff{i}a]"

            filters = []
            if track.volume != self.config.effects_volume:
                db = 20 * (track.volume if track.volume > 0 else 0.0001).log10()
                filters.append(f"volume={db}dB")

            if filters:
                filter_complex.append(f"{label}{','.join(filters)}{processed}")
            else:
                filter_complex.append(f"{label}{processed}")

        # 收集所有处理后的标签
        all_labels = [input_labels[0]]  # 静音底床
        all_labels.extend([f"[d{i}a]" for i in range(len(dialogue_segments))])
        all_labels.extend([f"[bg{i}a]" for i in range(len(background_tracks))])
        all_labels.extend([f"[amb{i}a]" for i in range(len(ambient_tracks))])
        all_labels.extend([f"[eff{i}a]" for i in range(len(effects_tracks))])
        if original_vocals:
            all_labels.append(input_labels[-1])

        # 混合所有音轨
        total_inputs = len(all_labels)
        mixed_label = "[mixed]"
        filter_complex.append(f"{''.join(all_labels)}amix=inputs={total_inputs}:duration=first:normalize=0{mixed_label}")

        # 应用滤镜
        filter_str = ";".join(filter_complex)
        cmd.extend(["-filter_complex", filter_str])
        cmd.extend([
            "-map", mixed_label,
            "-c:a", "pcm_s16le",
            "-ar", str(self.config.audio_sample_rate),
            str(output_path),
        ])

        # 执行命令
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"Audio mixing failed: {error_msg}")

        logger.info(f"Audio mixed successfully: {output_path}")
        return output_path
