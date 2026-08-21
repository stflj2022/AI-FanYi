"""Identity resolution from media hints."""

import logging
import re
from pathlib import Path
from typing import Optional

from filmdub.workers.research.config import get_research_config

logger = logging.getLogger(__name__)


class IdentityResolver:
    """Resolve show/season/episode identity from file metadata."""

    # Patterns for extracting season/episode from filenames
    SEASON_EPISODE_PATTERNS = [
        r'[Ss](\d{1,2})[Ee](\d{1,2})',  # S01E01
        r'[Ss]E(\d{1,2})\.(\d{1,2})',  # SE01.01
        r'(\d{1,2})x(\d{1,2})',  # 1x01
        r'Season\s*(\d{1,2})\s*Episode\s*(\d{1,2})',  # Season 1 Episode 1
        r'第(\d{1,2})季\s*第(\d{1,2})集',  # 第1季第1集
        r'[Ee][Pp]?[Ii]?sodes?\s*(\d{1,2})',  # Episode 1
    ]

    def __init__(self):
        """Initialize identity resolver."""
        self.config = get_research_config()

    def parse_filename(self, filename: str) -> dict[str, Optional[int]]:
        """Parse filename to extract title, season, episode.
        
        Args:
            filename: Filename to parse.
            
        Returns:
            dict: Parsed info with 'title', 'season', 'episode' keys.
        """
        result = {
            'title': None,
            'season': None,
            'episode': None,
            'confidence': 0.0
        }

        # Remove file extension
        name = Path(filename).stem

        # Try to extract season/episode
        for pattern in self.SEASON_EPISODE_PATTERNS:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                try:
                    result['season'] = int(match.group(1))
                    result['episode'] = int(match.group(2))
                    # Remove the matched pattern from title
                    title_part = re.sub(pattern, '', name, flags=re.IGNORECASE)
                    # Clean up title
                    result['title'] = self._clean_title(title_part)
                    result['confidence'] = 0.8
                    break
                except (ValueError, IndexError):
                    continue

        # If no season/episode found, try to extract just title
        if result['title'] is None:
            result['title'] = self._clean_title(name)

        return result

    def _clean_title(self, title: str) -> Optional[str]:
        """Clean up title by removing common patterns.
        
        args:
            title: Raw title string.
            
        Returns:
            Cleaned title or None.
        """
        if not title:
            return None

        # Remove common patterns
        # Quality tags
        title = re.sub(r'\.?\d{3,4}[pP]', '', title)
        title = re.sub(r'\d{3,4}[xX]\d{3,4}', '', title)
        title = re.sub(r'WEB[-\s]?DL', '', title, flags=re.IGNORECASE)
        title = re.sub(r'WEBRip', '', title, flags=re.IGNORECASE)
        title = re.sub(r'BluRay|BDRip|REMUX', '', title, flags=re.IGNORECASE)
        title = re.sub(r'HDTV|PDTV|DVDRip', '', title, flags=re.IGNORECASE)

        # Codec tags
        title = re.sub(r'\.x264|\.x265|\.H\.264|\.H\.265|\.HEVC', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\.XviD|\.DivX|\.VP9', '', title, flags=re.IGNORECASE)

        # Audio/Video technical terms
        title = re.sub(r'BD|DTS|HEVC|1080P|720P|480P', '', title, flags=re.IGNORECASE)
        title = re.sub(r'Dolby|AC3|AAC|MP3|FLAC', '', title, flags=re.IGNORECASE)
        title = re.sub(r'5\.1|7\.1|2\.0|Stereo', '', title)

        # Subtitle language indicators
        title = re.sub(r'简英双语|中英双字|繁体|简体', '', title)
        title = re.sub(r'Chinese|English|Chi|Eng', '', title, flags=re.IGNORECASE)

        # Season indicators
        title = re.sub(r'[Ss](\d{1,2})[Ee](\d{1,2})', '', title)
        title = re.sub(r'(\d{1,2})x(\d{1,2})', '', title)
        title = re.sub(r'Season|Series', '', title, flags=re.IGNORECASE)

        # Release group (usually in brackets)
        title = re.sub(r'\[.*?\]|\(.*?\)', '', title)

        # Replace separators with spaces
        title = re.sub(r'[._\-]+', ' ', title)

        # Collapse multiple spaces
        title = re.sub(r'\s+', ' ', title).strip()

        # Extract English title if mixed Chinese-English
        # Try to find English words pattern
        english_parts = re.findall(r'[A-Za-z][A-Za-z0-9\s]*', title)
        if english_parts:
            english_title = ' '.join(english_parts).strip()
            if english_title:
                return english_title

        # Handle empty result
        return title if title else None

    def guess_title_from_context(self, project_title: str | None) -> str | None:
        """Use project title as context.
        
        Args:
            project_title: Project title from Module 01.
            
        Returns:
            Project title or None.
        """
        return project_title

    def resolve_identity(
        self,
        filename: str | None = None,
        project_title: str | None = None,
        duration: float | None = None
    ) -> dict:
        """Resolve show identity from available hints.
        
        Args:
            filename: Original filename.
            project_title: Project title from Module 01.
            duration: Media duration in seconds.
            
        Returns:
            dict: Resolved identity info.
        """
        identity = {
            'title': None,
            'season': None,
            'episode': None,
            'year': None,
            'tmdb_candidates': [],
            'confidence': 0.0,
            'source': 'project_title' if project_title else 'filename'
        }

        # Priority 1: Use project title (most reliable)
        if project_title:
            identity['title'] = project_title
            identity['confidence'] = 0.8
            identity['source'] = 'project_title'

        # Priority 2: Parse filename for season/episode
        if filename:
            parsed = self.parse_filename(filename)
            # If we don't have a title yet, use the parsed one
            if not identity['title']:
                identity['title'] = parsed['title']
                identity['confidence'] = parsed['confidence']
                identity['source'] = 'filename'
            # Always use season/episode from filename
            if parsed['season'] is not None:
                identity['season'] = parsed['season']
                identity['confidence'] = max(identity['confidence'], 0.8)
            if parsed['episode'] is not None:
                identity['episode'] = parsed['episode']
                identity['confidence'] = max(identity['confidence'], 0.8)

        # Priority 3: Estimate year from duration (very rough heuristic)
        if duration and not identity['year']:
            # 50-60 min episodes suggest 2000s+
            # 40-50 min suggests 1990s-2000s
            # <30 min suggests 1990s or older
            if duration > 3600:
                identity['year'] = 2005  # Modern TV hour-long episodes
            elif duration > 2400:
                identity['year'] = 2000
            else:
                identity['year'] = 1995

        return identity
