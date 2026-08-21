"""Research sources module."""

from .tmdb import get_tmdb_adapter
from .wikidata import get_wikidata_adapter, WikidataAdapter
from .web_search import get_web_search_adapter, WebSearchAdapter

__all__ = [
    "get_tmdb_adapter",
    "get_wikidata_adapter",
    "WikidataAdapter",
    "get_web_search_adapter",
    "WebSearchAdapter",
]
