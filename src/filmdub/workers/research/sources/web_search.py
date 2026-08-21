"""Web search adapter for research worker."""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup

from core.config import settings
from workers.research.config import get_research_config

logger = logging.getLogger(__name__)


class WebSearchAdapter:
    """Adapter for web search and content extraction."""

    def __init__(self, project_id: str):
        """Initialize web search adapter.

        Args:
            project_id: Project ID.
        """
        self.config = get_research_config()
        self.project_id = project_id
        self.projects_dir = settings.projects_base_dir
        self.cache_dir = self.projects_dir / project_id / "research" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, url: str) -> str:
        """Get cache key for a URL.

        Args:
            url: URL to cache.

        Returns:
            str: Cache key.
        """
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def _get_cache_path(self, url: str) -> Path:
        """Get cache file path for a URL.

        Args:
            url: URL to cache.

        Returns:
            Path: Cache file path.
        """
        cache_key = self._get_cache_key(url)
        return self.cache_dir / f"{cache_key}.json"

    def _load_from_cache(self, url: str) -> Optional[dict]:
        """Load cached content for a URL.

        Args:
            url: URL to load.

        Returns:
            dict: Cached content or None.
        """
        cache_path = self._get_cache_path(url)
        if not cache_path.exists():
            return None

        try:
            with cache_path.open("r") as f:
                cached = json.load(f)

            logger.info(f"Cache HIT: {url}")
            return cached
        except Exception as e:
            logger.warning(f"Failed to load cache for {url}: {e}")
            return None

    def _save_to_cache(self, url: str, content: str, status: int = 200) -> dict:
        """Save content to cache.

        Args:
            url: URL.
            content: Content to cache.
            status: HTTP status code.

        Returns:
            dict: Cached data.
        """
        cache_path = self._get_cache_path(url)
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        cached = {
            "url": url,
            "retrieved_at": datetime.utcnow().isoformat(),
            "status": status,
            "content_hash": content_hash,
            "text": content,
        }

        try:
            with cache_path.open("w") as f:
                json.dump(cached, f, indent=2)
            logger.info(f"Cache saved: {url}")
        except Exception as e:
            logger.warning(f"Failed to save cache for {url}: {e}")

        return cached

    async def fetch_url(self, url: str, use_cache: bool = True) -> Optional[dict]:
        """Fetch content from a URL.

        Args:
            url: URL to fetch.
            use_cache: Whether to use cache.

        Returns:
            dict: Document data or None.
        """
        # Try cache first
        if use_cache:
            cached = self._load_from_cache(url)
            if cached:
                return cached

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; FilmDub/1.0; Research Worker)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                # Extract text content
                soup = BeautifulSoup(response.text, "html.parser")
                text = self._extract_text(soup)

                # Save to cache
                cached = self._save_to_cache(url, text, response.status_code)

                return cached

        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract readable text from HTML.

        Args:
            soup: BeautifulSoup object.

        Returns:
            str: Extracted text.
        """
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            element.decompose()

        # Get text
        text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        return text

    async def search(self, query: str, num_results: int = 5) -> list[dict]:
        """Search the web (placeholder for actual search API).

        Note: This is a simplified version. In production, integrate with
        search APIs like Google Custom Search, Bing, DuckDuckGo, etc.

        Args:
            query: Search query.
            num_results: Number of results.

        Returns:
            list: Search results.
        """
        logger.info(f"Web search: {query}")

        # For now, use a simple approach with Wikipedia
        # In production, integrate with actual search APIs
        wikipedia_url = f"https://en.wikipedia.org/wiki/Special:Search?search={query}"

        document = await self.fetch_url(wikipedia_url)
        if not document:
            return []

        return [{
            "url": wikipedia_url,
            "title": query,
            "snippet": document.get("text", "")[:500],
            "source_id": f"src_web_{self._get_cache_key(wikipedia_url)}",
        }]

    async def search_character(self, character_name: str, work_title: str) -> list[dict]:
        """Search for character information.

        Args:
            character_name: Character name.
            work_title: Work title.

        Returns:
            list: Search results.
        """
        queries = [
            f'"{character_name}" "{work_title}" character',
            f'"{character_name}" {work_title}',
            f'Who plays {character_name} in {work_title}',
        ]

        results = []
        for query in queries:
            query_results = await self.search(query, num_results=2)
            results.extend(query_results)

        return results

    async def search_actor(self, actor_name: str, work_title: Optional[str] = None) -> list[dict]:
        """Search for actor information.

        Args:
            actor_name: Actor name.
            work_title: Optional work title.

        Returns:
            list: Search results.
        """
        if work_title:
            query = f'"{actor_name}" "{work_title}" cast'
        else:
            query = f'"{actor_name}" actor'

        return await self.search(query, num_results=5)

    async def search_work(self, title: str, season: Optional[int] = None, episode: Optional[int] = None) -> list[dict]:
        """Search for work information.

        Args:
            title: Work title.
            season: Optional season number.
            episode: Optional episode number.

        Returns:
            list: Search results.
        """
        if season is not None and episode is not None:
            query = f'"{title}" season {season} episode {episode} cast'
        else:
            query = f'"{title}" TV series cast'

        return await self.search(query, num_results=5)


# Factory function
def get_web_search_adapter(project_id: str) -> WebSearchAdapter:
    """Get a web search adapter instance.

    Args:
        project_id: Project ID.

    Returns:
        WebSearchAdapter: Adapter instance.
    """
    return WebSearchAdapter(project_id)
