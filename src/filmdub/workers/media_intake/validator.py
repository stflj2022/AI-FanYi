"""Media validation utilities."""

from pathlib import Path
from typing import Optional


class MediaValidationError(Exception):
    """Media validation error."""

    def __init__(self, code: str, message: str):
        """Initialize validation error.

        Args:
            code: Error code.
            message: Error message.
        """
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class MediaValidator:
    """Validates media files."""

    # File size limits (in bytes)
    MIN_FILE_SIZE = 1024  # 1KB minimum
    MAX_FILE_SIZE = 100 * 1024 * 1024 * 1024  # 100GB default (configurable)

    def __init__(self, max_file_size: Optional[int] = None):
        """Initialize media validator.

        Args:
            max_file_size: Maximum file size in bytes. Uses default if None.
        """
        self.max_file_size = max_file_size or self.MAX_FILE_SIZE

    def validate_file_exists(self, path: Path) -> None:
        """Validate that file exists.

        Args:
            path: File path.

        Raises:
            MediaValidationError: If file doesn't exist.
        """
        if not path.exists():
            raise MediaValidationError("FILE_NOT_FOUND", f"File does not exist: {path}")

    def validate_file_size(self, path: Path) -> int:
        """Validate file size.

        Args:
            path: File path.

        Returns:
            int: File size in bytes.

        Raises:
            MediaValidationError: If file size is invalid.
        """
        size = path.stat().st_size

        if size < self.MIN_FILE_SIZE:
            raise MediaValidationError(
                "FILE_TOO_SMALL",
                f"File is too small: {size} bytes (minimum: {self.MIN_FILE_SIZE})"
            )

        if size > self.max_file_size:
            raise MediaValidationError(
                "FILE_TOO_LARGE",
                f"File is too large: {size} bytes (maximum: {self.max_file_size})"
            )

        return size

    def validate_probe_result(self, probe_data: dict) -> None:
        """Validate FFprobe result.

        Args:
            probe_data: FFprobe output.

        Raises:
            MediaValidationError: If probe result is invalid.
        """
        if not probe_data:
            raise MediaValidationError("PROBE_FAILED", "FFprobe returned no data")

        if "streams" not in probe_data:
            raise MediaValidationError("NO_STREAMS", "No streams found in media")

        # Check for video stream
        has_video = any(s.get("codec_type") == "video" for s in probe_data["streams"])
        if not has_video:
            raise MediaValidationError("NO_VIDEO_STREAM", "No video stream found")

        # Check for audio stream
        has_audio = any(s.get("codec_type") == "audio" for s in probe_data["streams"])
        if not has_audio:
            raise MediaValidationError("NO_AUDIO_STREAM", "No audio stream found")

    def validate_duration(self, duration: Optional[float]) -> float:
        """Validate media duration.

        Args:
            duration: Duration in seconds.

        Returns:
            float: Validated duration.

        Raises:
            MediaValidationError: If duration is invalid.
        """
        if duration is None:
            raise MediaValidationError("NO_DURATION", "Could not determine media duration")

        if duration <= 0:
            raise MediaValidationError("INVALID_DURATION", f"Invalid duration: {duration}")

        if duration < 1.0:
            raise MediaValidationError("DURATION_TOO_SHORT", f"Duration too short: {duration}s")

        return duration

    def validate_all(self, path: Path, probe_data: dict) -> tuple[int, float]:
        """Run all validations.

        Args:
            path: File path.
            probe_data: FFprobe output.

        Returns:
            tuple: (file_size, duration)

        Raises:
            MediaValidationError: If any validation fails.
        """
        self.validate_file_exists(path)
        size = self.validate_file_size(path)
        self.validate_probe_result(probe_data)

        # Extract duration from probe data
        format_data = probe_data.get("format", {})
        duration_str = format_data.get("duration")

        duration = None
        if duration_str:
            try:
                duration = float(duration_str)
            except ValueError:
                pass

        if duration is None:
            # Try video stream
            video_streams = [s for s in probe_data.get("streams", []) if s.get("codec_type") == "video"]
            if video_streams:
                duration_str = video_streams[0].get("duration")
                if duration_str:
                    try:
                        duration = float(duration_str)
                    except ValueError:
                        pass

        duration = self.validate_duration(duration)

        return size, duration
