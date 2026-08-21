"""Manifest building utilities."""

from typing import Any

from filmdub.workers.media_intake.probe import FFprobeParser


def build_media_manifest(
    probe_data: dict[str, Any],
    media_id: str,
    filename: str,
    sha256: str,
    parser: FFprobeParser | None = None,
) -> dict[str, Any]:
    """Build media manifest from FFprobe data.

    Args:
        probe_data: FFprobe output.
        media_id: Media ID.
        filename: Original filename.
        sha256: File SHA-256 hash.
        parser: Optional FFprobeParser instance.

    Returns:
        dict: Media manifest.
    """
    if parser is None:
        parser = FFprobeParser()

    # Get streams
    video_streams = parser.get_video_streams(probe_data)
    audio_streams = parser.get_audio_streams(probe_data)
    subtitle_streams = parser.get_subtitle_streams(probe_data)

    # Select primary video stream
    primary_video = parser.select_default_video_stream(probe_data)

    # Build video info
    video_info = {}
    if primary_video:
        video_info = {
            "index": primary_video.get("index"),
            "codec": primary_video.get("codec_name"),
            "codec_long": primary_video.get("codec_long_name"),
            "width": primary_video.get("width"),
            "height": primary_video.get("height"),
            "fps": _parse_fps(primary_video.get("r_frame_rate")),
            "duration": _parse_duration(primary_video.get("duration")),
            "bit_rate": primary_video.get("bit_rate"),
            "pixel_format": primary_video.get("pix_fmt"),
            "is_default": primary_video.get("disposition", {}).get("default", False),
        }

    # Build audio streams info
    audio_info = []
    for stream in audio_streams:
        audio_info.append({
            "index": stream.get("index"),
            "codec": stream.get("codec_name"),
            "codec_long": stream.get("codec_long_name"),
            "language": parser.get_stream_language(stream),
            "title": stream.get("tags", {}).get("title"),
            "channels": stream.get("channels"),
            "channel_layout": stream.get("channel_layout"),
            "sample_rate": stream.get("sample_rate"),
            "bit_rate": stream.get("bit_rate"),
            "duration": _parse_duration(stream.get("duration")),
            "is_default": stream.get("disposition", {}).get("default", False),
            "is_forced": stream.get("disposition", {}).get("forced", False),
        })

    # Build subtitle streams info
    subtitle_info = []
    for stream in subtitle_streams:
        subtitle_info.append({
            "index": stream.get("index"),
            "codec": stream.get("codec_name"),
            "codec_long": stream.get("codec_long_name"),
            "language": parser.get_stream_language(stream),
            "title": stream.get("tags", {}).get("title"),
            "is_default": stream.get("disposition", {}).get("default", False),
            "is_forced": stream.get("disposition", {}).get("forced", False),
        })

    # Build chapters info
    chapters = parser.get_chapters(probe_data)
    chapter_info = [
        {
            "id": ch.get("id"),
            "start": _parse_time_base(ch.get("start"), ch.get("time_base")),
            "end": _parse_time_base(ch.get("end"), ch.get("time_base")),
            "title": ch.get("tags", {}).get("title"),
        }
        for ch in chapters
    ]

    # Get format info
    format_info = parser.get_format_info(probe_data)

    # Build manifest
    manifest = {
        "schema_version": "1.0",
        "media_id": media_id,
        "filename": filename,
        "sha256": sha256,
        "container": {
            "format": format_info.get("format_name"),
            "format_long": format_info.get("format_long_name"),
            "duration": format_info.get("duration"),
            "size_bytes": format_info.get("size_bytes"),
            "bit_rate": format_info.get("bit_rate"),
        },
        "video": video_info,
        "audio": audio_info,
        "subtitles": subtitle_info,
        "chapters": chapter_info,
    }

    return manifest


def _parse_fps(fps_str: str | None) -> float | None:
    """Parse FPS string to float.

    Args:
        fps_str: FPS string (e.g., "24000/1001" or "29.97").

    Returns:
        Optional[float]: FPS value or None.
    """
    if not fps_str:
        return None

    try:
        if "/" in fps_str:
            num, den = fps_str.split("/")
            return float(num) / float(den)
        return float(fps_str)
    except (ValueError, ZeroDivisionError):
        return None


def _parse_duration(duration_str: str | None) -> float | None:
    """Parse duration string to float.

    Args:
        duration_str: Duration string.

    Returns:
        Optional[float]: Duration in seconds or None.
    """
    if not duration_str:
        return None
    try:
        return float(duration_str)
    except ValueError:
        return None


def _parse_time_base(time_str: str | None, time_base: str | None) -> float | None:
    """Parse time with time base to seconds.

    Args:
        time_str: Time string.
        time_base: Time base string (e.g., "1/1000").

    Returns:
        Optional[float]: Time in seconds or None.
    """
    if not time_str or not time_base:
        return None

    try:
        time = float(time_str)
        if "/" in time_base:
            num, den = time_base.split("/")
            base = float(num) / float(den)
        else:
            base = float(time_base)
        return time * base
    except (ValueError, ZeroDivisionError):
        return None
