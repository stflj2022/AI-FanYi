"""
视频组装器

使用 FFmpeg 替换视频音频、嵌入字幕并最终编码
"""
import subprocess
import json
import os
import tempfile
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

from .models import AudioSegment, SubtitleEntry, AssemblyResult
from .config import M11Config


class VideoAssembler:
    """视频组装器"""

    def __init__(self, config: M11Config = None):
        """
        初始化组装器

        Args:
            config: M11 配置
        """
        self.config = config or M11Config()

        # 验证 FFmpeg 是否可用
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """检查 FFmpeg 是否可用"""
        try:
            result = subprocess.run(
                [self.config.ffmpeg_path, "-version"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise RuntimeError("FFmpeg not found")

            logger.info(f"FFmpeg detected: {result.stdout.split()[2]}")

        except FileNotFoundError:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.")

    async def assemble_video(
        self,
        source_video_path: str,
        audio_segments: List[AudioSegment],
        output_path: str,
        subtitles: Optional[List[SubtitleEntry]] = None,
        project_id: str = "",
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> AssemblyResult:
        """
        组装视频

        Args:
            source_video_path: 源视频路径
            audio_segments: 音频片段列表
            output_path: 输出路径
            subtitles: 字幕列表（可选）
            project_id: 项目 ID（写入结果）
            progress_callback: 进度回调

        Returns:
            组装结果
        """
        logger.info(f"Assembling video: {source_video_path} -> {output_path}")

        temp_video_path: Optional[str] = None
        combined_audio_path: Optional[str] = None

        try:
            # 1. 获取视频信息
            video_info = await self._get_video_info(source_video_path)

            # 2. 创建合成音频轨道
            combined_audio_path = await self._create_combined_audio(
                audio_segments,
                video_info["duration"],
                progress_callback
            )

            # 3. 替换音频 → 写入临时文件（避免与最终输出同路径，字幕嵌入阶段才能安全覆盖）
            with tempfile.NamedTemporaryFile(
                suffix=Path(output_path).suffix or ".mp4", delete=False
            ) as tmp:
                temp_video_path = tmp.name

            await self._replace_audio(
                source_video_path,
                combined_audio_path,
                temp_video_path,
                progress_callback
            )

            # 4. 嵌入字幕（如果需要）
            final_video_path = temp_video_path
            subtitle_path = None

            if subtitles:
                subtitle_path = await self._embed_subtitles(
                    temp_video_path,
                    subtitles,
                    output_path,
                    progress_callback
                )
                final_video_path = output_path
            else:
                # 无字幕时直接把临时文件移动到最终路径
                os.replace(temp_video_path, output_path)
                temp_video_path = None  # 已移动，无需清理
                final_video_path = output_path

            # 5. 获取最终视频信息
            final_info = await self._get_video_info(final_video_path)

            # 6. 构建结果
            result = AssemblyResult(
                project_id=project_id,
                video_path=final_video_path,
                duration=float(final_info["duration"]),
                resolution=f"{final_info['width']}x{final_info['height']}",
                file_size=os.path.getsize(final_video_path),
                audio_codec=self.config.audio_codec,
                video_codec=self.config.video_codec,
                subtitle_path=subtitle_path
            )

            logger.info(f"Video assembled successfully: {final_video_path}")

            return result

        except Exception as e:
            logger.error(f"Video assembly failed: {e}")
            raise

        finally:
            # 7. 清理临时文件
            for path in (combined_audio_path, temp_video_path):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    async def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        获取视频信息

        Args:
            video_path: 视频路径

        Returns:
            视频信息字典
        """
        cmd = [
            self.config.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to get video info: {result.stderr}")

        info = json.loads(result.stdout)

        # 提取关键信息
        format_info = info.get("format", {})

        # 查找视频流
        video_stream = next(
            (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
            {}
        )

        return {
            "duration": float(format_info.get("duration", 0)),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "video_codec": video_stream.get("codec_name", ""),
            "audio_codec": next(
                (s.get("codec_name", "") for s in info.get("streams", [])
                 if s.get("codec_type") == "audio"),
                ""
            ),
        }

    async def _create_combined_audio(
        self,
        audio_segments: List[AudioSegment],
        video_duration: float,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """
        创建合成音频轨道

        Args:
            audio_segments: 音频片段列表
            video_duration: 视频时长
            progress_callback: 进度回调

        Returns:
            合成音频路径
        """
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        # 构建复杂滤镜
        filter_complex = []

        # 输入文件
        inputs = []

        for segment in audio_segments:
            inputs.extend(["-i", segment.audio_path])

        # 创建输入标签
        input_labels = [f"[{i}a]" for i in range(len(audio_segments))]

        # 为每个片段创建淡入淡出
        for i, (segment, label) in enumerate(zip(audio_segments, input_labels)):
            # 计算延迟
            delay = segment.target_start_time

            # 添加延迟滤镜
            delayed_label = f"[d{i}a]"
            filter_complex.append(f"{label}adelay={int(delay * 1000)}|{int(delay * 1000)}{delayed_label}")

        # 混合所有音频
        mixed_label = "[mixed]"
        all_delayed = [f"[d{i}a]" for i in range(len(audio_segments))]
        mix_inputs = "".join(all_delayed)
        filter_complex.append(f"{mix_inputs}amix=inputs={len(audio_segments)}:duration=first{mixed_label}")

        # 构建命令
        cmd = [
            self.config.ffmpeg_path,
            "-y"  # 覆盖输出文件
        ]

        # 添加输入
        for segment in audio_segments:
            cmd.extend(["-i", segment.audio_path])

        # 添加滤镜
        filter_str = ";".join(filter_complex)
        cmd.extend(["-filter_complex", filter_str])

        # 编码设置
        cmd.extend([
            "-map", mixed_label,
            "-c:a", "pcm_s16le",
            "-ar", str(self.config.audio_sample_rate),
            temp_path
        ])

        # 执行命令
        subprocess.run(cmd, check=True, capture_output=True)

        # 更新进度
        if progress_callback:
            progress_callback(0.5)

        logger.info(f"Combined audio created: {temp_path}")

        return temp_path

    async def _replace_audio(
        self,
        source_video_path: str,
        audio_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """
        替换视频音频

        Args:
            source_video_path: 源视频路径
            audio_path: 音频路径
            output_path: 输出路径
            progress_callback: 进度回调

        Returns:
            输出路径
        """
        cmd = [
            self.config.ffmpeg_path,
            "-y",  # 覆盖输出文件
            "-i", source_video_path,  # 视频输入
            "-i", audio_path,  # 音频输入
            "-c:v", "copy",  # 复制视频流（不重新编码）
            "-c:a", self.config.audio_codec,  # 音频编码
            "-b:a", self.config.audio_bitrate,  # 音频比特率
            "-ar", str(self.config.audio_sample_rate),  # 音频采样率
            "-map", "0:v:0",  # 使用第一个视频流
            "-map", "1:a:0",  # 使用第二个音频流
            "-shortest",  # 以最短的流为准
            output_path
        ]

        # 执行命令
        subprocess.run(cmd, check=True, capture_output=True)

        # 更新进度
        if progress_callback:
            progress_callback(0.8)

        logger.info(f"Audio replaced: {output_path}")

        return output_path

    async def _embed_subtitles(
        self,
        video_path: str,
        subtitles: List[SubtitleEntry],
        output_path: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """
        嵌入字幕

        Args:
            video_path: 视频路径
            subtitles: 字幕列表
            output_path: 输出路径
            progress_callback: 进度回调

        Returns:
            字幕文件路径
        """
        # 创建字幕文件
        subtitle_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".ass",
            delete=False,
            encoding="utf-8"
        )

        # 写入 ASS 头部
        subtitle_file.write(
            "[Script Info]\n"
            "Title: Subtitles\n"
            "ScriptType: v4.00+\n"
            "WrapStyle: 0\n"
            "PlayResX: 1920\n"
            "PlayResY: 1080\n"
            "ScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\n"
            f"Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Default,{self.config.subtitle_font},{self.config.subtitle_font_size},{self.config.subtitle_color},&H000000FF,{self.config.subtitle_outline_color},&H80000000,0,0,0,0,100,100,0,0,1,{self.config.subtitle_outline_width},0,2,10,10,10,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )

        # 写入字幕条目
        for i, subtitle in enumerate(subtitles):
            subtitle_file.write(subtitle.to_ass() + "\n")

        subtitle_file.close()

        # 嵌入字幕
        cmd = [
            self.config.ffmpeg_path,
            "-y",
            "-i", video_path,
            "-vf", f"ass={subtitle_file.name}",
            "-c:a", "copy",  # 不重新编码音频
            "-c:v", self.config.video_codec,
            "-preset", self.config.video_preset,
            "-crf", str(self.config.crf),
            output_path
        ]

        # 执行命令
        subprocess.run(cmd, check=True, capture_output=True)

        # 清理字幕文件
        os.remove(subtitle_file.name)

        # 更新进度
        if progress_callback:
            progress_callback(1.0)

        logger.info(f"Subtitles embedded: {output_path}")

        return output_path

    async def encode_video(
        self,
        input_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ):
        """
        重新编码视频

        Args:
            input_path: 输入路径
            output_path: 输出路径
            progress_callback: 进度回调
        """
        cmd = [
            self.config.ffmpeg_path,
            "-y",
            "-i", input_path,
            "-c:v", self.config.video_codec,
            "-preset", self.config.video_preset,
            "-crf", str(self.config.crf),
            "-b:v", self.config.video_bitrate,
            "-c:a", self.config.audio_codec,
            "-b:a", self.config.audio_bitrate,
            output_path
        ]

        # 执行命令
        subprocess.run(cmd, check=True, capture_output=True)

        logger.info(f"Video encoded: {output_path}")
