"""
M12 视频封装 Worker

将中文对白、背景音、字幕组装成最终的 mp4 视频
"""
from __future__ import annotations

import subprocess
import os
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional, List

from .config import M12Config
from .models import (
    EncapsulationInput,
    EncapsulationResult,
    AudioTrack,
    SubtitleTrack,
    VideoQuality,
    SubtitleMode
)

logger = logging.getLogger(__name__)


class VideoEncapsulationWorker:
    """视频封装 Worker"""

    def __init__(self, config: M12Config = None):
        """
        初始化 Worker

        Args:
            config: M12 配置
        """
        self.config = config or M12Config()
        self._ensure_temp_dir()

    def _ensure_temp_dir(self):
        """确保临时目录存在"""
        os.makedirs(self.config.temp_dir, exist_ok=True)

    def process(self, input_data: EncapsulationInput) -> EncapsulationResult:
        """
        处理视频封装

        Args:
            input_data: 封装输入

        Returns:
            封装结果
        """
        try:
            logger.info(f"开始视频封装: {input_data.video_file} -> {input_data.output_file}")

            # 验证输入文件
            self._validate_inputs(input_data)

            # 构建 FFmpeg 命令
            ffmpeg_cmd = self._build_ffmpeg_command(input_data)

            # 执行 FFmpeg
            logger.info(f"执行 FFmpeg 命令: {' '.join(ffmpeg_cmd)}")
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )

            if result.returncode != 0:
                error_msg = f"FFmpeg 执行失败: {result.stderr}"
                logger.error(error_msg)
                return EncapsulationResult(
                    success=False,
                    output_file=input_data.output_file,
                    duration=0,
                    size_bytes=0,
                    resolution="",
                    fps=0,
                    error_message=error_msg
                )

            # 获取输出文件信息
            output_info = self._get_video_info(input_data.output_file)

            logger.info(f"视频封装成功: {input_data.output_file}")

            return EncapsulationResult(
                success=True,
                output_file=input_data.output_file,
                duration=output_info.get("duration", 0),
                size_bytes=output_info.get("size", 0),
                video_bitrate=output_info.get("video_bitrate"),
                audio_bitrate=output_info.get("audio_bitrate"),
                resolution=output_info.get("resolution", ""),
                fps=output_info.get("fps", 0)
            )

        except subprocess.TimeoutExpired:
            error_msg = "FFmpeg 执行超时"
            logger.error(error_msg)
            return EncapsulationResult(
                success=False,
                output_file=input_data.output_file,
                duration=0,
                size_bytes=0,
                resolution="",
                fps=0,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"视频封装失败: {str(e)}"
            logger.error(error_msg)
            return EncapsulationResult(
                success=False,
                output_file=input_data.output_file,
                duration=0,
                size_bytes=0,
                resolution="",
                fps=0,
                error_message=error_msg
            )

    def _validate_inputs(self, input_data: EncapsulationInput):
        """验证输入文件"""
        # 检查视频文件
        if not os.path.exists(input_data.video_file):
            raise FileNotFoundError(f"视频文件不存在: {input_data.video_file}")

        # 检查音轨文件
        for track in input_data.audio_tracks:
            if not os.path.exists(track.file_path):
                raise FileNotFoundError(f"音频文件不存在: {track.file_path}")

        # 检查字幕文件
        if input_data.subtitle_track and not os.path.exists(input_data.subtitle_track.file_path):
            raise FileNotFoundError(f"字幕文件不存在: {input_data.subtitle_track.file_path}")

        # 检查输出目录
        output_dir = os.path.dirname(input_data.output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

    def _build_ffmpeg_command(self, input_data: EncapsulationInput) -> List[str]:
        """构建 FFmpeg 命令"""
        cmd = [self.config.ffmpeg_path]

        # 输入文件
        cmd.extend(["-i", input_data.video_file])

        # 添加音轨
        for track in input_data.audio_tracks:
            cmd.extend(["-i", track.file_path])

        # 视频编码参数
        cmd.extend([
            "-c:v", self.config.video_codec,
            "-preset", self.config.preset,
            "-crf", str(self.config.crf),
        ])

        # 分辨率
        if self.config.scale:
            cmd.extend(["-vf", f"scale={self.config.scale}"])
        elif input_data.quality and input_data.quality.width and input_data.quality.height:
            scale = f"{input_data.quality.width}:{input_data.quality.height}"
            cmd.extend(["-vf", f"scale={scale}"])

        # 帧率
        fps = input_data.quality.fps if input_data.quality and input_data.quality.fps else self.config.fps
        cmd.extend(["-r", str(fps)])

        # 码率
        video_bitrate = (input_data.quality.bitrate if input_data.quality and input_data.quality.bitrate
                        else self.config.video_bitrate)
        cmd.extend(["-b:v", video_bitrate])

        # 音频混音
        if input_data.audio_tracks:
            # 构建混音 filter
            audio_filter_parts = []
            for i, track in enumerate(input_data.audio_tracks):
                track_idx = i + 1  # 0 是视频，从 1 开始是音频
                volume = track.volume if track.volume != 1.0 else 1.0
                if volume != 1.0:
                    audio_filter_parts.append(f"[{track_idx}:a]volume={volume}[a{i}]")
                else:
                    audio_filter_parts.append(f"[{track_idx}:a]acopy[a{i}]")

            # 混合所有音轨
            mix_inputs = "".join([f"[a{i}]" for i in range(len(input_data.audio_tracks))])
            audio_filter = ";".join(audio_filter_parts) + f";{mix_inputs}amix=inputs={len(input_data.audio_tracks)}[aout]"
            cmd.extend(["-filter_complex", audio_filter])
            cmd.extend(["-map", "0:v", "-map", "[aout]"])
        else:
            # 使用原始音频
            cmd.extend(["-map", "0:v", "-map", "0:a"])

        # 音频编码
        cmd.extend([
            "-c:a", self.config.audio_codec,
            "-b:a", self.config.audio_bitrate,
        ])

        # 字幕
        if input_data.subtitle_track:
            if input_data.subtitle_track.mode == SubtitleMode.HARD:
                # 硬字幕：烧录到视频中
                subtitle_file = input_data.subtitle_track.file_path
                # 简单的硬字幕实现（需要安装字幕滤镜）
                cmd.extend(["-vf", f"subtitles={subtitle_file}"])
            else:
                # 软字幕：独立轨道
                cmd.extend(["-i", input_data.subtitle_track.file_path])
                cmd.extend(["-c:s", "mov_text"])
                cmd.extend(["-map", "0:v", "-map", "1:a?", "-map", "2:s?"])

        # 其他参数
        cmd.extend(["-movflags", "+faststart"])  # 优化 mp4 播放
        cmd.extend(["-y"])  # 覆盖输出文件
        cmd.append(input_data.output_file)

        return cmd

    def _get_video_info(self, video_file: str) -> dict:
        """获取视频文件信息"""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate",
                "-show_entries", "format=duration,size,bit_rate",
                "-of", "json",
                video_file
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return {}

            import json
            info = json.loads(result.stdout)

            # 提取信息
            output = {}
            if "streams" in info and info["streams"]:
                stream = info["streams"][0]
                output["width"] = stream.get("width")
                output["height"] = stream.get("height")
                output["resolution"] = f"{stream.get('width', 0)}x{stream.get('height', 0)}"
                if "r_frame_rate" in stream:
                    fps_str = stream["r_frame_rate"]
                    if "/" in fps_str:
                        num, den = fps_str.split("/")
                        output["fps"] = float(num) / float(den)
                    else:
                        output["fps"] = float(fps_str)

            if "format" in info:
                fmt = info["format"]
                output["duration"] = float(fmt.get("duration", 0))
                output["size"] = int(fmt.get("size", 0))
                bitrate = fmt.get("bit_rate")
                if bitrate:
                    bitrate_int = int(bitrate)
                    output["video_bitrate"] = f"{bitrate_int // 1000}k"
                    output["audio_bitrate"] = f"{bitrate_int // 10000}k"

            return output

        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
            return {}

    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 检查 FFmpeg 是否可用
            result = subprocess.run(
                [self.config.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def close(self):
        """关闭 Worker，清理资源"""
        logger.info("关闭 VideoEncapsulationWorker")
        # 清理临时文件
        if os.path.exists(self.config.temp_dir):
            try:
                shutil.rmtree(self.config.temp_dir)
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")
