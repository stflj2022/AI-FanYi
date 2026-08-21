"""TMDB API adapter for film/TV show research."""

import asyncio
import logging
from typing import Any, Optional

import httpx

from workers.research.config import get_research_config

logger = logging.getLogger(__name__)


class TMBDAdapter:
    """TMDB API adapter."""

    BASE_URL = "https://api.themoviedb.org/3"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize TMDB adapter.
        
        Args:
            api_key: TMDB API key. If None, reads from config.
        """
        config = get_research_config()
        self.api_key = api_key or config.tmdb_api_key
        
        if not self.api_key:
            logger.warning("TMDB API key not configured")
        
        self.timeout = config.request_timeout
        self.reliability = config.reliability_tmdb
    
    async def search_tv_show(self, query: str) -> dict[str, Any] | None:
        """Search for a TV show.
        
        Args:
            query: Search query.
            
        Returns:
            Search results or None if failed.
        """
        if not self.api_key:
            return None
        
        params = {
            "api_key": self.api_key,
            "query": query,
            "language": "en-US",
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search/tv",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"TMDB search for '{query}': {len(data.get('results', []))} results")
                return data
        except Exception as e:
            logger.error(f"TMDB search failed: {e}")
            return None
    
    async def get_tv_details(self, tmdb_id: int) -> dict[str, Any] | None:
        """Get TV show details.
        
        Args:
            tmdb_id: TMDB show ID.
            
        Returns:
            Show details or None if failed.
        """
        if not self.api_key:
            return None
        
        params = {
            "api_key": self.api_key,
            "language": "en-US",
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/tv/{tmdb_id}",
                    params=params
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"TMDB get show details failed: {e}")
            return None
    
    async def get_season_details(self, tmdb_id: int, season_number: int) -> dict[str, Any] | None:
        """Get season details.
        
        args:
            tmdb_id: TMDB show ID.
            season_number: Season number.
            
        Returns:
            Season details or None if failed.
        """
        if not self.api_key:
            return None
        
        params = {
            "api_key": self.api_key,
            "language": "en-US",
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/tv/{tmdb_id}/season/{season_number}",
                    params=params
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"TMDB get season details failed: {e}")
            return None
    
    async def get_episode_details(
        self,
        tmdb_id: int,
        season_number: int,
        episode_number: int
    ) -> dict[str, Any] | None:
        """Get episode details.
        
        Args:
            tmdb_id: TMDB show ID.
            season_number: Season number.
            episode_number: Episode number.
            
        Returns:
            Episode details or None if failed.
        """
        if not self.api_key:
            return None
        
        params = {
            "api_key": self.api_key,
            "language": "en-US",
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/tv/{tmdb_id}/season/{season_number}/episode/{episode_number}",
                    params=params
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"TMDB get episode details failed: {e}")
            return None
    
    async def get_tv_credits(self, tmdb_id: int) -> dict[str, Any] | None:
        """Get TV show credits (cast).
        
        Args:
            tmdb_id: TMDB show ID.
            
        Returns:
            Credits data or None if failed.
        """
        if not self.api_key:
            return None
        
        params = {
            "api_key": self.api_key,
            "language": "en-US",
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/tv/{tmdb_id}/credits",
                    params=params
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"TMDB get credits failed: {e}")
            return None


# Singleton instance
_tmdb_adapter: Optional[TMBDAdapter] = None


def get_tmdb_adapter() -> TMBDAdapter:
    """Get or create TMDB adapter instance.
    
    Returns:
        TMBDAdapter: TMDB adapter instance.
    """
    global _tmdb_adapter
    if _tmdb_adapter is None:
        _tmdb_adapter = TMBDAdapter()
    return _tmdb_adapter
