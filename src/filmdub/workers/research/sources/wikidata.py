"""Wikidata adapter for research worker."""

import logging
from typing import Any, Optional

import httpx

from workers.research.config import get_research_config

logger = logging.getLogger(__name__)


class WikidataAdapter:
    """Adapter for Wikidata API."""

    def __init__(self):
        """Initialize Wikidata adapter."""
        self.config = get_research_config()
        self.base_url = "https://www.wikidata.org/w/api.php"
        self.sparql_url = "https://query.wikidata.org/sparql"

    async def search_entity(self, query: str, entity_type: str = "Q5") -> Optional[dict]:
        """Search for an entity on Wikidata.

        Args:
            query: Search query.
            entity_type: Wikidata entity type (Q5=human, Q11424=film, etc.).

        Returns:
            dict: Entity data or None if not found.
        """
        try:
            # Search via MediaWiki API
            params = {
                "action": "wbsearchentities",
                "search": query,
                "language": "en",
                "format": "json",
                "limit": 5,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

            if not data.get("search"):
                logger.warning(f"No Wikidata results for: {query}")
                return None

            # Find best match (prefer matching entity type)
            for result in data["search"]:
                if entity_type in result.get("description", ""):
                    return await self.get_entity_details(result["id"])

            # Return first result if no type match
            return await self.get_entity_details(data["search"][0]["id"])

        except Exception as e:
            logger.error(f"Wikidata search failed: {e}")
            return None

    async def get_entity_details(self, entity_id: str) -> Optional[dict]:
        """Get detailed information about a Wikidata entity.

        Args:
            entity_id: Wikidata entity ID (e.g., "Q42").

        Returns:
            dict: Entity details or None if not found.
        """
        try:
            params = {
                "action": "wbgetentities",
                "ids": entity_id,
                "format": "json",
                "props": "labels|descriptions|claims|sitelinks",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

            if entity_id not in data.get("entities", {}):
                logger.warning(f"Wikidata entity not found: {entity_id}")
                return None

            entity = data["entities"][entity_id]
            return self._parse_entity(entity)

        except Exception as e:
            logger.error(f"Wikidata entity details failed: {e}")
            return None

    def _parse_entity(self, entity: dict) -> dict:
        """Parse Wikidata entity data.

        Args:
            entity: Raw entity data from Wikidata.

        Returns:
            dict: Parsed entity data.
        """
        labels = entity.get("labels", {})
        descriptions = entity.get("descriptions", {})
        claims = entity.get("claims", {})
        sitelinks = entity.get("sitelinks", {})

        parsed = {
            "id": entity["id"],
            "labels": {k: v["value"] for k, v in labels.items()},
            "descriptions": {k: v["value"] for k, v in descriptions.items()},
            "claims": {},
            "sitelinks": list(sitelinks.keys()),
        }

        # Parse claims
        for prop_id, claim_list in claims.items():
            if not claim_list:
                continue

            claim = claim_list[0]
            mainsnak = claim.get("mainsnak", {})
            datatype = mainsnak.get("datatype")
            datavalue = mainsnak.get("datavalue", {})

            if datavalue:
                if datatype == "string":
                    value = datavalue.get("value", "")
                elif datatype == "wikibase-item":
                    value = datavalue.get("value", {}).get("id", "")
                elif datatype == "time":
                    value = datavalue.get("value", {}).get("time", "")
                elif datatype == "monolingualtext":
                    value = datavalue.get("value", {}).get("text", "")
                elif datatype == "quantity":
                    value = datavalue.get("value", {}).get("amount", "")
                else:
                    value = str(datavalue.get("value", ""))

                parsed["claims"][prop_id] = value

        return parsed

    async def get_actor_info(self, name: str) -> Optional[dict]:
        """Get actor information from Wikidata.

        Args:
            name: Actor name.

        Returns:
            dict: Actor info or None.
        """
        entity = await self.search_entity(name, entity_type="Q5")  # Q5 = human
        if not entity:
            return None

        actor_info = {
            "wikidata_id": entity["id"],
            "name": entity["labels"].get("en", ""),
            "description": entity["descriptions"].get("en", ""),
            "claims": entity.get("claims", {}),
            "wikipedia_link": f"https://en.wikipedia.org/wiki/{entity['sitelinks'][0]}" if entity.get("sitelinks") else None,
        }

        return actor_info

    async def get_character_info(self, name: str, work_title: str) -> Optional[dict]:
        """Get character information from Wikidata.

        Args:
            name: Character name.
            work_title: Work title.

        Returns:
            dict: Character info or None.
        """
        # Try SPARQL query for fictional characters
        sparql_query = f"""
        SELECT ?item ?itemLabel ?description ?portrayedBy ?portrayedByLabel
        WHERE {{
            ?item rdfs:label "{name}"@en.
            ?item wdt:P31 wd:Q95074.  # fictional character
            OPTIONAL {{ ?item wdt:P161 ?portrayedBy. }}
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 5
        """

        try:
            params = {
                "query": sparql_query,
                "format": "json",
            }

            headers = {
                "User-Agent": "FilmDub/1.0 (Research Worker)",
                "Accept": "application/sparql-results+json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.sparql_url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()

            results = data.get("results", {}).get("bindings", [])
            if not results:
                logger.warning(f"No Wikidata character results for: {name}")
                return None

            # Parse first result
            result = results[0]
            character_info = {
                "wikidata_id": result.get("item", {}).get("value", "").split("/")[-1],
                "name": result.get("itemLabel", {}).get("value", ""),
                "description": result.get("description", {}).get("value", ""),
                "portrayed_by": result.get("portrayedByLabel", {}).get("value", ""),
                "portrayed_by_id": result.get("portrayedBy", {}).get("value", "").split("/")[-1] if result.get("portrayedBy") else None,
            }

            return character_info

        except Exception as e:
            logger.error(f"Wikidata SPARQL query failed: {e}")
            return None

    async def get_work_info(self, title: str) -> Optional[dict]:
        """Get TV show/movie information from Wikidata.

        Args:
            title: Work title.

        Returns:
            dict: Work info or None.
        """
        # Search for TV series (Q21191270) or film (Q11424)
        entity = await self.search_entity(title)
        if not entity:
            return None

        claims = entity.get("claims", {})

        work_info = {
            "wikidata_id": entity["id"],
            "title": entity["labels"].get("en", ""),
            "description": entity["descriptions"].get("en", ""),
            "imdb_id": claims.get("P345", ""),  # P345 = IMDb ID
            "tmdb_id": claims.get("P4947", ""),  # P4947 = TMDb ID
            "genre": claims.get("P136", ""),  # P136 = genre
            "country_of_origin": claims.get("P495", ""),  # P495 = country of origin
            "cast": claims.get("P161", ""),  # P161 = cast member
            "creator": claims.get("P57", ""),  # P57 = director/creator
            "wikipedia_link": f"https://en.wikipedia.org/wiki/{entity['sitelinks'][0]}" if entity.get("sitelinks") else None,
        }

        return work_info


# Singleton instance
_wikidata_adapter: Optional[WikidataAdapter] = None


def get_wikidata_adapter() -> WikidataAdapter:
    """Get the singleton Wikidata adapter instance.

    Returns:
        WikidataAdapter: The adapter instance.
    """
    global _wikidata_adapter
    if _wikidata_adapter is None:
        _wikidata_adapter = WikidataAdapter()
    return _wikidata_adapter
