"""Translation memory implementation."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from difflib import SequenceMatcher

from .models import TranslationMemoryEntry, TermEntry

logger = logging.getLogger(__name__)


class TranslationMemory:
    """Translation memory for storing and retrieving translations."""

    def __init__(self, path: str = "data/translation_memory.json"):
        """Initialize translation memory."""
        self.path = Path(path)
        self.entries: List[TranslationMemoryEntry] = []
        self.glossary: List[TermEntry] = []
        self._load()

    def _load(self):
        """Load translation memory from file."""
        try:
            if self.path.exists():
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.entries = [
                        TranslationMemoryEntry(**entry) for entry in data.get("entries", [])
                    ]
                    self.glossary = [
                        TermEntry(**term) for term in data.get("glossary", [])
                    ]
                logger.info(f"Loaded {len(self.entries)} translation memory entries")
            else:
                # Create empty file
                self._save()
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to load translation memory: {e}")
            self.entries = []
            self.glossary = []
            # Create new file
            self._save()

    def _save(self):
        """Save translation memory to file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "entries": [
                        {
                            "id": str(entry.id),
                            "source_text": entry.source_text,
                            "translated_text": entry.translated_text,
                            "source_lang": entry.source_lang,
                            "target_lang": entry.target_lang,
                            "context": entry.context,
                            "usage_count": entry.usage_count,
                            "last_used": entry.last_used.isoformat() if hasattr(entry.last_used, 'isoformat') else entry.last_used,
                            "created_at": entry.created_at.isoformat() if hasattr(entry.created_at, 'isoformat') else entry.created_at,
                        }
                        for entry in self.entries
                    ],
                    "glossary": [
                        {
                            "source_term": term.source_term,
                            "target_term": term.target_term,
                            "category": term.category,
                            "notes": term.notes,
                            "created_at": term.created_at.isoformat() if hasattr(term.created_at, 'isoformat') else term.created_at,
                        }
                        for term in self.glossary
                    ],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

    def find_translation(
        self,
        source_text: str,
        source_lang: str = "en",
        target_lang: str = "zh",
        similarity_threshold: float = 0.85,
    ) -> Optional[TranslationMemoryEntry]:
        """Find a translation in memory with similarity matching."""
        source_text_normalized = source_text.strip().lower()

        best_match = None
        best_score = 0.0

        for entry in self.entries:
            if entry.source_lang != source_lang or entry.target_lang != target_lang:
                continue

            score = SequenceMatcher(
                None, entry.source_text.lower(), source_text_normalized
            ).ratio()

            if score > best_score and score >= similarity_threshold:
                best_score = score
                best_match = entry

        if best_match:
            # Update usage count
            best_match.usage_count += 1
            from datetime import datetime

            best_match.last_used = datetime.utcnow()
            self._save()

        return best_match

    def add_translation(
        self,
        source_text: str,
        translated_text: str,
        source_lang: str = "en",
        target_lang: str = "zh",
        context: str = "",
    ) -> TranslationMemoryEntry:
        """Add a translation to memory."""
        from datetime import datetime
        from uuid import uuid4

        entry = TranslationMemoryEntry(
            id=uuid4(),
            source_text=source_text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            context=context,
            usage_count=1,
            last_used=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )

        self.entries.append(entry)
        self._save()

        logger.debug(f"Added translation memory entry: {source_text[:50]}...")
        return entry

    def add_term(
        self,
        source_term: str,
        target_term: str,
        category: str = "",
        notes: str = "",
    ) -> TermEntry:
        """Add a term to glossary."""
        from datetime import datetime

        term = TermEntry(
            source_term=source_term,
            target_term=target_term,
            category=category,
            notes=notes,
            created_at=datetime.utcnow(),
        )

        self.glossary.append(term)
        self._save()

        logger.debug(f"Added glossary term: {source_term} -> {target_term}")
        return term

    def find_term(self, source_term: str) -> Optional[TermEntry]:
        """Find a term in glossary."""
        source_term_normalized = source_term.strip().lower()

        for term in self.glossary:
            if term.source_term.lower() == source_term_normalized:
                return term

        return None

    def apply_glossary(self, text: str, source_lang: str = "en") -> Dict[str, str]:
        """Find and return glossary terms in text."""
        terms_found = {}

        for term in self.glossary:
            if term.source_term.lower() in text.lower():
                terms_found[term.source_term] = term.target_term

        return terms_found

    def get_statistics(self) -> Dict:
        """Get translation memory statistics."""
        return {
            "total_entries": len(self.entries),
            "total_glossary_terms": len(self.glossary),
            "language_pairs": self._get_language_pairs(),
            "most_used": self._get_most_used(),
        }

    def _get_language_pairs(self) -> List[Dict]:
        """Get statistics by language pair."""
        pairs: Dict[str, int] = {}

        for entry in self.entries:
            pair = f"{entry.source_lang}->{entry.target_lang}"
            pairs[pair] = pairs.get(pair, 0) + 1

        return [{"pair": k, "count": v} for k, v in sorted(pairs.items())]

    def _get_most_used(self, limit: int = 10) -> List[Dict]:
        """Get most used translations."""
        sorted_entries = sorted(
            self.entries, key=lambda e: e.usage_count, reverse=True
        )

        return [
            {
                "source": entry.source_text[:50] + "..."
                if len(entry.source_text) > 50
                else entry.source_text,
                "target": entry.translated_text[:50] + "..."
                if len(entry.translated_text) > 50
                else entry.translated_text,
                "usage_count": entry.usage_count,
            }
            for entry in sorted_entries[:limit]
        ]
