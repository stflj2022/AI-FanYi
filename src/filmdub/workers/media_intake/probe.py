"""FFprobe media analysis."""

import json
import subprocess
from pathlib import Path
from typing import Any, Optional

from filmdub.core.config import settings


class FFprobeError(Exception):
    """FFprobe execution error."""

    pass


class FFprobeParser:
    """Parse media files using FFprobe."""

    def __init__(self, ffprobe_path: Optional[str] = None):
        """Initialize FFprobe parser.

        Args:
            ffprobe_path: Path to ffprobe executable. Uses config default if None.
        """
        self.ffprobe_path = ffprobe_path or settings.ffprobe_path

    def probe(self, media_path: Path) -> dict[str, Any]:
        """Probe media file with FFprobe.

        Args:
            media_path: Path to media file.

        Returns:
            dict: Parsed FFprobe output.

        Raises:
            FFprobeError: If FFprobe fails.
        """
        if not media_path.exists():
            raise FFprobeError(f"Media file not found: {media_path}")

        cmd = [
            str(self.ffprobe_path),
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            "-show_chapters",
            str(media_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise FFprobeError(f"FFprobe failed: {e.stderr}") from e
        except FileNotFoundError:
            raise FFprobeError(f"FFprobe not found at: {self.ffprobe_path}")

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise FFprobeError(f"Failed to parse FFprobe JSON output: {e}") from e

    def get_video_streams(self, probe_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract video streams from probe data.

        Args:
            probe_data: FFprobe output.

        Returns:
            list: Video streams.
        """
        return [
            stream for stream in probe_data.get("streams", [])
            if stream.get("codec_type") == "video"
        ]

    def get_audio_streams(self, probe_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract audio streams from probe data.

        Args:
            probe_data: FFprobe output.

        Returns:
            list: Audio streams.
        """
        return [
            stream for stream in probe_data.get("streams", [])
            if stream.get("codec_type") == "audio"
        ]

    def get_subtitle_streams(self, probe_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract subtitle streams from probe data.

        Args:
            probe_data: FFprobe output.

        Returns:
            list: Subtitle streams.
        """
        return [
            stream for stream in probe_data.get("streams", [])
            if stream.get("codec_type") == "subtitle"
        ]

    def get_duration(self, probe_data: dict[str, Any]) -> Optional[float]:
        """Get media duration from probe data.

        Args:
            probe_data: FFprobe output.

        Returns:
            Optional[float]: Duration in seconds.
        """
        # Try format first, then video stream
        duration = probe_data.get("format", {}).get("duration")
        if duration:
            try:
                return float(duration)
            except ValueError:
                pass

        # Fall back to first video stream
        video_streams = self.get_video_streams(probe_data)
        if video_streams:
            duration = video_streams[0].get("duration")
            if duration:
                try:
                    return float(duration)
                except ValueError:
                    pass

        return None

    def get_format_info(self, probe_data: dict[str, Any]) -> dict[str, Any]:
        """Get format information from probe data.

        Args:
            probe_data: FFprobe output.

        Returns:
            dict: Format information.
        """
        format_data = probe_data.get("format", {})
        return {
            "format_name": format_data.get("format_name"),
            "format_long_name": format_data.get("format_long_name"),
            "duration": self.get_duration(probe_data),
            "size_bytes": format_data.get("size"),
            "bit_rate": format_data.get("bit_rate"),
        }

    def get_chapters(self, probe_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Get chapters from probe data.

        Args:
            probe_data: FFprobe output.

        Returns:
            list: Chapters.
        """
        return probe_data.get("chapters", [])

    def select_default_video_stream(self, probe_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Select the default video stream.

        Args:
            probe_data: FFprobe output.

        Returns:
            Optional[dict]: Default video stream, or None.
        """
        video_streams = self.get_video_streams(probe_data)
        if not video_streams:
            return None

        # First try to find one with default disposition
        for stream in video_streams:
            disposition = stream.get("disposition", {})
            if disposition.get("default"):
                return stream

        # Fall back to highest resolution
        def resolution(stream: dict[str, Any]) -> int:
            w = stream.get("width", 0) or 0
            h = stream.get("height", 0) or 0
            return w * h

        return max(video_streams, key=resolution)

    def get_stream_language(self, stream: dict[str, Any]) -> Optional[str]:
        """Get stream language code.

        Args:
            stream: Stream data.

        Returns:
            Optional[str]: Language code (e.g., 'eng', 'chi').
        """
        # Try tags.language first
        tags = stream.get("tags", {})
        if "language" in tags:
            return tags["language"]

        return None
