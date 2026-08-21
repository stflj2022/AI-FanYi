"""Qwen LLM extraction module for research worker."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx

from workers.research.config import get_research_config

logger = logging.getLogger(__name__)


class QwenExtractor:
    """Qwen LLM-based entity extraction."""

    def __init__(self, project_id: str):
        """Initialize Qwen extractor.

        Args:
            project_id: Project ID.
        """
        self.project_id = project_id
        self.config = get_research_config()
        self.api_url = self.config.qwen_api_url or "http://localhost:11434/api/generate"
        self.model = self.config.qwen_model or "qwen2.5:7b"

    async def _call_llm(self, prompt: str, temperature: float = 0.1) -> Optional[str]:
        """Call LLM API.

        Args:
            prompt: Prompt to send.
            temperature: Temperature for generation.

        Returns:
            str: LLM response or None.
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
                "max_tokens": 4096,
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()
                data = response.json()

            return data.get("response", "")

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None

    def _build_extraction_prompt(self, task: str, context: str, documents: list[dict]) -> str:
        """Build extraction prompt.

        Args:
            task: Task description.
            context: Context information.
            documents: List of documents with text.

        Returns:
            str: Formatted prompt.
        """
        # Prepare document text
        docs_text = "\n\n".join([
            f"[Source {i+1}: {doc.get('title', 'Untitled')}]\n{doc.get('text', '')[:2000]}"
            for i, doc in enumerate(documents[:5])  # Limit to 5 documents
        ])

        prompt = f"""You are a research assistant for film and TV shows. Your task is to {task}.

# Context
{context}

# Evidence
{docs_text}

# Instructions
1. ONLY use the evidence provided above.
2. DO NOT use your own knowledge or make assumptions.
3. DO NOT create characters, actors, or relationships that are not in the evidence.
4. Each fact MUST cite the source (e.g., "source_id": "src_001").
5. Output ONLY valid JSON, no markdown formatting.

# Output Format
```json
{{
  "characters": [
    {{
      "name": "Character Name",
      "actor": "Actor Name",
      "aliases": ["Alias 1", "Alias 2"],
      "description": "Brief description",
      "evidence": ["src_001", "src_002"]
    }}
  ],
  "relationships": [
    {{
      "subject": "Character A",
      "relation": "spouse",
      "object": "Character B",
      "evidence": ["src_003"]
    }}
  ],
  "confidence": 0.95
}}
```

# Allowed Relationship Types
- spouse (husband, wife, partner)
- parent (mother, father)
- child (son, daughter)
- sibling (brother, sister)
- friend
- partner (business partner, crime partner)
- employer
- employee
- enemy
- relative
- colleague
- associate

Now, analyze the evidence and extract the information:
"""

        return prompt

    async def extract_characters(
        self,
        work_title: str,
        documents: list[dict],
        existing_characters: Optional[list[dict]] = None,
    ) -> dict:
        """Extract characters from documents.

        Args:
            work_title: Title of the work.
            documents: List of research documents.
            existing_characters: Existing character data for reference.

        Returns:
            dict: Extracted character data.
        """
        context = f"Work: {work_title}"

        if existing_characters:
            context += f"\n\nExisting characters (do not duplicate):\n" + "\n".join([
                f"- {c.get('name', 'Unknown')}"
                for c in existing_characters
            ])

        prompt = self._build_extraction_prompt(
            "extract characters and their actors",
            context,
            documents
        )

        logger.info("Extracting characters with Qwen...")
        response = await self._call_llm(prompt)

        if not response:
            logger.warning("Qwen extraction returned no response")
            return {"characters": [], "relationships": [], "confidence": 0.0}

        # Parse JSON response
        try:
            # Extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                logger.info(f"Extracted {len(result.get('characters', []))} characters")
                return result
            else:
                logger.warning("No JSON found in Qwen response")
                return {"characters": [], "relationships": [], "confidence": 0.0}

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Qwen JSON response: {e}")
            logger.debug(f"Response: {response}")
            return {"characters": [], "relationships": [], "confidence": 0.0}

    async def extract_relationships(
        self,
        work_title: str,
        documents: list[dict],
        characters: list[dict],
    ) -> list[dict]:
        """Extract character relationships from documents.

        Args:
            work_title: Title of the work.
            documents: List of research documents.
            characters: List of known characters.

        Returns:
            list: Extracted relationships.
        """
        # Build character list
        char_list = "\n".join([f"- {c.get('name', 'Unknown')}" for c in characters])

        context = f"Work: {work_title}\n\nKnown characters:\n{char_list}"

        prompt = self._build_extraction_prompt(
            "extract character relationships",
            context,
            documents
        )

        logger.info("Extracting relationships with Qwen...")
        response = await self._call_llm(prompt)

        if not response:
            logger.warning("Qwen extraction returned no response")
            return []

        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                relationships = result.get("relationships", [])
                logger.info(f"Extracted {len(relationships)} relationships")
                return relationships
            else:
                return []

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Qwen JSON response: {e}")
            return []

    async def validate_entity(
        self,
        entity_type: str,
        entity_name: str,
        documents: list[dict],
    ) -> dict:
        """Validate an entity against evidence.

        Args:
            entity_type: Type of entity (character, actor, etc.).
            entity_name: Name of the entity.
            documents: List of research documents.

        Returns:
            dict: Validation result.
        """
        docs_text = "\n\n".join([
            f"[Source {i+1}]\n{doc.get('text', '')[:1000]}"
            for i, doc in enumerate(documents[:3])
        ])

        prompt = f"""You are a fact-checker. Verify if the following {entity_type} exists in the evidence:

{entity_type}: {entity_name}

# Evidence
{docs_text}

# Instructions
1. Check if there is evidence for this {entity_type}.
2. Rate your confidence (0.0 to 1.0).
3. List the source IDs that support this.
4. Output ONLY valid JSON.

# Output Format
```json
{{
  "exists": true/false,
  "confidence": 0.95,
  "evidence_sources": ["src_001", "src_002"],
  "reasoning": "Brief explanation"
}}
```

Now, analyze and respond:
"""

        response = await self._call_llm(prompt)

        if not response:
            return {"exists": False, "confidence": 0.0, "evidence_sources": [], "reasoning": "No LLM response"}

        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {"exists": False, "confidence": 0.0, "evidence_sources": [], "reasoning": "No JSON in response"}

        except json.JSONDecodeError:
            return {"exists": False, "confidence": 0.0, "evidence_sources": [], "reasoning": "Invalid JSON"}


# Factory function
def get_qwen_extractor(project_id: str) -> QwenExtractor:
    """Get a Qwen extractor instance.

    Args:
        project_id: Project ID.

    Returns:
        QwenExtractor: Extractor instance.
    """
    return QwenExtractor(project_id)
