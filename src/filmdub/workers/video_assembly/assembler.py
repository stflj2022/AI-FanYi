"""
视频组装器

使用 FFmpeg 替换音频、同步音视频、嵌入字幕
"""
import subprocess
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from loguru import logger

from .config import M11Config
from .models import VideoArtifact, AudioSyncPoint, AssemblyResult


class VideoAssembler:
    """视频组装器"""

    def __init__(self, config: M11Config = None):
        """
        初始化组装器

        Args:
            config: M11 配置
        """
        self.config = config or M11Config()

        # 验证 FFmpeg
        self._verify_ffmpeg()

    def assemble_video(
        self,
        input_video_path: str,
        audio_artifacts: List[Dict[str, Any]],
        output_video_path: str,
        subtitles: Optional[List[Dict[str, Any]]] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> AssemblyResult:
        """
        组装视频

        Args:
            input_video_path: 输入视频路径
            audio_artifacts: 音频 Artifact 列表
            output_video_path: 输出视频路径
            subtitles: 字幕列表
            progress_callback: 进度回调

        Returns:
            组装结果
        """
        logger.info(
            f"Assembling video: {input_video_path} -> {output_video_path}"
        )

        try:
            # 1. 获取视频信息
            video_info = self._get_video_info(input_video_path)
            logger.info(f"Video info: {video_info}")

            # 2. 合并音频
            merged_audio_path = self._merge_audio_tracks(
                audio_artifacts,
                video_info["duration"]
            )

            if not merged_audio_path:
                raise RuntimeError("Failed to merge audio tracks")

            # 3. 替换音频轨道
            intermediate_video = self._replace_audio(
                input_video_path,
                merged_audio_path,
                output_video_path
            )

            if not intermediate_video:
                raise RuntimeError("Failed to replace audio")

            # 4. 嵌入字幕（如果启用）
            if subtitles and self.config.enable_subtitles:
                final_video = self._embed_subtitles(
                    intermediate_video,
                    subtitles,
                    output_video_path
                )

                # 清理中间文件
                if final_video != intermediate_video:
                    Path(intermediate_video).unlink(missing_ok=True)
            else:
                final_video = intermediate_video

            # 5. 获取最终视频信息
            final_info = self._get_video_info(final_video)
            file_size = Path(final_video).stat().st_size

            # 6. 创建 Artifact
            artifact = VideoArtifact(
                artifact_id=f"video_{Path(output_video_path).stem}",
                project_id="",  # TODO: 从上下文获取
                file_path=final_video,
                duration=final_info["duration"],
                width=final_info["width"],
                height=final_info["height"],
                fps=final_info["fps"],
                file_size=file_size
            )

            logger.info(f"Video assembly completed: {final_video}")

            return AssemblyResult(
                status="success",
                video_artifact=artifact,
                metadata=final_info
            )

        except Exception as e:
            logger.error(f"Video assembly failed: {e}")
            return AssemblyResult(
                status="error",
                error=str(e)
            )

    def _verify_ffmpeg(self):
        """验证 FFmpeg 是否可用"""
        try:
            result = subprocess.run(
                [self.config.ffmpeg_path, "-version"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.info(f"FFmpeg found: {result.stdout.splitlines()[0]}")
            else:
                raise RuntimeError("FFmpeg not found")

        except FileNotFoundError:
            raise RuntimeError(
                f"FFmpeg not found at {self.config.ffmpeg_path}. "
                "Please install FFmpeg and ensure it's in your PATH."
            )

    def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        获取视频信息

        Args:
            video_path: 视频路径

        Returns:
            视频信息
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
        video_stream = next(
            (s for s in info["streams"] if s["codec_type"] == "video"),
            None
        )
        audio_stream = next(
            (s for s in info["streams"] if s["codec_type"] == "audio"),
            None
        )

        return {
            "duration": float(info["format"].get("duration", 0)),
            "width": video_stream.get("width", 0) if video_stream else 0,
            "height": video_stream.get("height", 0) if video_stream else 0,
            "fps": eval(video_stream.get("r_frame_rate", "0/1")) if video_stream else 0,
            "video_codec": video_stream.get("codec_name", "") if video_stream else "",
            "audio_codec": audio_stream.get("codec_name", "") if audio_stream else ""
        }

    def _merge_audio_tracks(
        self,
        audio_artifacts: List[Dict[str, Any]],
        target_duration: float
    ) -> Optional[str]:
        """
        合并音频轨道

        Args:
            audio_artifacts: 音频 Artifact 列表
            target_duration: 目标时长

        Returns:
            合并后的音频路径
        """
        if not audio_artifacts:
            return None

        # 按时间排序
        sorted_artifacts = sorted(
            audio_artifacts,
            key=lambda x: x.get("start_time", 0)
        )

        # 创建 concat 列表
        concat_file = "/tmp/ffmpeg_concat.txt"
        with open(concat_file, "w") as f:
            for artifact in sorted_artifacts:
                file_path = artifact.get("file_path")
                duration = artifact.get("duration", 0)

                if file_path and Path(file_path).exists():
                    f.write(f"file '{file_path}'\n")
                    f.write(f"duration {duration}\n")

        # 输出路径
        output_path = "/tmp/merged_audio.wav"

        # FFmpeg 命令
        cmd = [
            self.config.ffmpeg_path,
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c:a", "pcm_s16le",
            "-ar", str(self.config.audio_sample_rate),
            "-ac", str(self.config.audio_channels),
            "-y",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Failed to merge audio: {result.stderr}")
            return None

        logger.info(f"Audio merged: {output_path}")

        return output_path

    def _replace_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str
    ) -> Optional[str]:
        """
        替换音频轨道

        Args:
            video_path: 视频路径
            audio_path: 音频路径
            output_path: 输出路径

        Returns:
            输出视频路径
        """
        # FFmpeg 命令
        cmd = [
            self.config.ffmpeg_path,
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", self.config.audio_codec,
            "-b:a", self.config.audio_bitrate,
            "-ar", str(self.config.audio_sample_rate),
            "-ac", str(self.config.audio_channels),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-y",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Failed to replace audio: {result.stderr}")
            return None

        logger.info(f"Audio replaced: {output_path}")

        return output_path

    def _embed_subtitles(
        self,
        video_path: str,
        subtitles: List[Dict[str, Any]],
        output_path: str
    ) -> Optional[str]:
        """
        嵌入字幕

        Args:
            video_path: 视频路径
            subtitles: 字幕列表
            output_path: 输出路径

        Returns:
            输出视频路径
        """
        # 创建 SRT 字幕文件
        srt_path = "/tmp/subtitles.srt"
        self._create_srt_file(subtitles, srt_path)

        # FFmpeg 命令
        cmd = [
            self.config.ffmpeg_path,
            "-i", video_path,
            "-vf", f"subtitles={srt_path}:force_style='FontName={self.config.subtitle_font},FontSize={self.config.subtitle_font_size},PrimaryColour=&H{self.config.subtitle_font_color}'",
            "-c:a", "copy",
            "-y",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Failed to embed subtitles: {result.stderr}")
            return video_path  # 返回原视频

        logger.info(f"Subtitles embedded: {output_path}")

        return output_path

    def _create_srt_file(self, subtitles: List[Dict[str, Any]], output_path: str):
        """
        创建 SRT 字幕文件

        Args:
            subtitles: 字幕列表
            output_path: 输出路径
        """
        def format_time(seconds: float) -> str:
            """格式化时间为 SRT 格式"""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

        with open(output_path, "w", encoding="utf-8") as f:
            for i, sub in enumerate(subtitles, 1):
                start_time = sub.get("start_time", 0)
                end_time = sub.get("end_time", start_time)
                text = sub.get("text", "")

                f.write(f"{i}\n")
                f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
                f.write(f"{text}\n\n")
