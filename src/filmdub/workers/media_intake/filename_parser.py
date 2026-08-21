"""Filename parsing utilities."""

import re
from pathlib import Path
from typing import Optional

from core.schemas import FilenameParseResult


# Patterns for detecting season/episode numbers
SEASON_EPISODE_PATTERNS = [
    r"[Ss](\d{1,2})[Ee](\d{1,2})",  # S01E01
    r"(\d{1,2})x(\d{1,2})",  # 1x01
    r"Season\s*(\d{1,2})\s*Episode\s*(\d{1,2})",  # Season 1 Episode 1
    r"第(\d{1,2})季\s*第(\d{1,2})集",  # 第1季第1集
]

# Patterns for quality tags
QUALITY_PATTERNS = [
    r"2160p|4K",
    r"1080p|FHD|FullHD",
    r"720p|HD",
    r"480p|SD",
    r"360p",
    r"240p",
]

# Patterns for source tags
SOURCE_PATTERNS = [
    r"WEB[- ]?DL|WEB-DL",
    r"WEBRip|WEB-Rip",
    r"BluRay|BDRip|BDRemux",
    r"DVD|R5|DVDScr",
    r"HDTV|PDTV",
    r"TS|TC|CAM",
]

# Patterns for codec tags
CODEC_PATTERNS = [
    r"x265|H\.265|HEVC",
    r"x264|H\.264|AVC",
    r"VP9",
    r"AV1",
    r"XviD|DivX",
]

# Pattern for release group (usually at end in brackets)
RELEASE_GROUP_PATTERN = r"\[([^\]]+)\]$|\(([^\)]+)\)$"


def parse_filename(filename: str) -> FilenameParseResult:
    """Parse a media filename to extract metadata.

    Args:
        filename: Filename to parse.

    Returns:
        FilenameParseResult: Parsed information.
    """
    stem = Path(filename).stem

    result = FilenameParseResult()

    # Try to extract season/episode
    for pattern in SEASON_EPISODE_PATTERNS:
        match = re.search(pattern, stem, re.IGNORECASE)
        if match:
            result.season = int(match.group(1))
            result.episode = int(match.group(2))
            break

    # Try to extract quality
    for pattern in QUALITY_PATTERNS:
        match = re.search(pattern, stem, re.IGNORECASE)
        if match:
            result.quality = match.group(0).upper()
            break

    # Try to extract source
    for pattern in SOURCE_PATTERNS:
        match = re.search(pattern, stem, re.IGNORECASE)
        if match:
            result.source = match.group(0).upper()
            break

    # Try to extract codec
    for pattern in CODEC_PATTERNS:
        match = re.search(pattern, stem, re.IGNORECASE)
        if match:
            result.codec = match.group(0).upper()
            break

    # Try to extract release group
    match = re.search(RELEASE_GROUP_PATTERN, stem)
    if match:
        result.release_group = match.group(1) or match.group(2)

    # Extract title candidate (everything before first S/E/pattern)
    title_parts = []
    for pattern in SEASON_EPISODE_PATTERNS + QUALITY_PATTERNS:
        parts = re.split(pattern, stem, flags=re.IGNORECASE, maxsplit=1)
        if len(parts) > 1:
            title_parts.append(parts[0].rstrip(".-_ "))
            break

    if title_parts:
        # Clean up title
        title = title_parts[0]
        title = re.sub(r"[._\-]+", " ", title)  # Replace separators with spaces
        title = re.sub(r"\s+", " ", title).strip()  # Collapse multiple spaces
        result.title_candidate = title if title else None

    # Adjust confidence based on what we found
    confidence = 0.5
    if result.season and result.episode:
        confidence += 0.2
    if result.title_candidate:
        confidence += 0.2
    if result.quality and result.source:
        confidence += 0.1

    result.confidence = min(confidence, 1.0)

    return result


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing problematic characters.

    Args:
        filename: Original filename.

    Returns:
        str: Sanitized filename.
    """
    # Remove path traversal attempts
    filename = filename.replace("..", "").replace("/", "").replace("\\", "")

    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Trim whitespace
    filename = filename.strip()

    return filename
