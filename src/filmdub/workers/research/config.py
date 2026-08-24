"""Research worker configuration and utilities."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ResearchConfig:
    """Research worker configuration."""

    # API Keys
    tmdb_api_key: Optional[str] = None
    omdb_api_key: Optional[str] = None
    
    # Cache settings
    cache_dir: Path = None
    cache_enabled: bool = True
    
    # Confidence thresholds
    confidence_threshold_merge: float = 0.90
    confidence_threshold_review: float = 0.70
    confidence_threshold_reject: float = 0.70
    
    # Source reliability (0-100)
    reliability_official: float = 100.0
    reliability_tmdb: float = 95.0
    reliability_wikidata: float = 95.0
    reliability_wikipedia: float = 90.0
    reliability_imdb: float = 85.0
    reliability_fandom: float = 70.0
    reliability_web: float = 50.0
    
    # Request settings
    request_timeout: int = 30
    max_retries: int = 3
    user_agent: str = "FilmDub-Research/1.0"
    
    # LLM settings
    llm_enabled: bool = False
    llm_model: str = "qwen"
    llm_base_url: str = "http://localhost:11434/v1"
    qwen_api_url: Optional[str] = None
    qwen_model: Optional[str] = None
    
    def __post_init__(self):
        if self.cache_dir is None:
            self.cache_dir = Path("./cache")
        
        # Load from environment (ignore placeholder values)
        tmdb_key = os.getenv("TMDB_API_KEY")
        if tmdb_key and tmdb_key not in ["your_tmdb_api_key_here", "", "none"]:
            self.tmdb_api_key = tmdb_key
        
        omdb_key = os.getenv("OMDB_API_KEY")
        if omdb_key and omdb_key not in ["your_omdb_api_key_here", "", "none"]:
            self.omdb_api_key = omdb_key
        
        self.llm_enabled = os.getenv("RESEARCH_LLM_ENABLED", "false").lower() == "true"
        self.llm_base_url = os.getenv("LLM_BASE_URL", self.llm_base_url)
        self.qwen_api_url = os.getenv("QWEN_API_URL") or self.qwen_api_url
        self.qwen_model = os.getenv("QWEN_MODEL") or self.qwen_model


def get_research_config() -> ResearchConfig:
    """Get research configuration from environment."""
    return ResearchConfig()
