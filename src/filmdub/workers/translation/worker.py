"""M06 Translation Worker implementation."""

import asyncio
import logging
from typing import Dict, List

from .config import get_config, TranslationConfig
from .engine import MockTranslationEngine, QwenTranslationEngine, TranslationEngine
from .memory import TranslationMemory
from .models import M06Input, M06Output, TranslationRequest, TranslationResult

logger = logging.getLogger(__name__)


class M06Worker:
    """M06 Translation Worker - translates dialogue to Chinese."""

    def __init__(
        self,
        config: TranslationConfig | None = None,
        engine: TranslationEngine | None = None,
        translation_memory: TranslationMemory | None = None,
    ):
        """Initialize M06 Worker."""
        self.config = config or get_config()
        self.engine = engine or self._create_engine()
        self.translation_memory = translation_memory or TranslationMemory(
            self.config.translation_memory_path
        )

    def _create_engine(self) -> TranslationEngine:
        """Create translation engine based on configuration."""
        if self.config.engine == "qwen":
            return QwenTranslationEngine(self.config)
        else:
            logger.warning(f"Unknown engine type: {self.config.engine}, using mock")
            return MockTranslationEngine(self.config)

    async def process(self, input_data: M06Input) -> M06Output:
        """Process translation task."""
        logger.info(f"Starting translation for project {input_data.project_id}")

        # Extract dialogues from timeline
        dialogues = input_data.dialogue_timeline

        # Prepare translation requests
        translation_requests = self._prepare_requests(
            dialogues, input_data.character_database
        )

        # Batch translate with translation memory
        results = await self._translate_with_memory(translation_requests)

        # Update dialogue timeline with translations
        translated_dialogues = self._update_dialogues(dialogues, results)

        # Collect statistics
        statistics = self._collect_statistics(results)

        # Get memory updates
        memory_updates = [r for r in results if hasattr(r, "memory_entry")]

        logger.info(
            f"Translation completed: {len(translated_dialogues)} dialogues translated"
        )

        return M06Output(
            project_id=input_data.project_id,
            job_id=input_data.job_id,
            translated_dialogues=translated_dialogues,
            translation_memory_updates=memory_updates,
            statistics=statistics,
        )

    def _prepare_requests(
        self, dialogues: List[Dict], character_database: Dict
    ) -> List[TranslationRequest]:
        """Prepare translation requests from dialogues."""
        requests = []

        for i, dialogue in enumerate(dialogues):
            text = dialogue.get("text", "")
            if not text:
                continue

            # Get context from previous and next lines
            context = self._build_context(dialogues, i)

            # Get character info
            character_id = dialogue.get("character_id")
            character_name = self._get_character_name(character_id, character_database)

            # Get emotion
            emotion = dialogue.get("emotion")

            request = TranslationRequest(
                text=text,
                source_lang=dialogue.get("source_lang", "en"),
                target_lang=dialogue.get("target_lang", "zh"),
                context=context,
                character_id=character_id,
                emotion=emotion,
            )

            requests.append(request)

        return requests

    def _build_context(self, dialogues: List[Dict], current_index: int) -> str:
        """Build context from surrounding dialogues."""
        context_parts = []

        # Previous lines
        for i in range(max(0, current_index - 2), current_index):
            if dialogues[i].get("text"):
                context_parts.append(f"{dialogues[i].get('text', '')}")

        # Next lines
        for i in range(current_index + 1, min(len(dialogues), current_index + 3)):
            if dialogues[i].get("text"):
                context_parts.append(f"{dialogues[i].get('text', '')}")

        return " | ".join(context_parts)

    def _get_character_name(
        self, character_id: str | None, character_database: Dict
    ) -> str | None:
        """Get character name from database."""
        if not character_id:
            return None

        for character in character_database.get("characters", []):
            if character.get("id") == character_id:
                return character.get("name")

        return None

    async def _translate_with_memory(
        self, requests: List[TranslationRequest]
    ) -> List[TranslationResult]:
        """Translate with translation memory."""
        results = []
        to_translate = []

        # First, check translation memory
        for request in requests:
            memory_entry = None

            if self.config.enable_translation_memory:
                memory_entry = self.translation_memory.find_translation(
                    source_text=request.text,
                    source_lang=request.source_lang,
                    target_lang=request.target_lang,
                    similarity_threshold=self.config.similarity_threshold,
                )

            if memory_entry:
                # Use translation from memory
                results.append(
                    TranslationResult(
                        original_text=request.text,
                        translated_text=memory_entry.translated_text,
                        source_lang=request.source_lang,
                        target_lang=request.target_lang,
                        confidence=0.95,  # High confidence for memory matches
                        used_memory=True,
                    )
                )
            else:
                # Need to translate
                to_translate.append((request, len(results)))
                results.append(None)  # Placeholder

        # Batch translate remaining requests
        if to_translate:
            translation_results = await self.engine.batch_translate(
                [req for req, _ in to_translate]
            )

            # Fill in results and add to memory
            for (request, original_index), result in zip(to_translate, translation_results):
                results[original_index] = result

                # Add to translation memory
                if self.config.enable_translation_memory and result.translated_text:
                    self.translation_memory.add_translation(
                        source_text=request.text,
                        translated_text=result.translated_text,
                        source_lang=request.source_lang,
                        target_lang=request.target_lang,
                        context=request.context or "",
                    )

        return results

    def _update_dialogues(
        self, dialogues: List[Dict], results: List[TranslationResult]
    ) -> List[Dict]:
        """Update dialogues with translations."""
        result_index = 0
        translated = []

        for dialogue in dialogues:
            if not dialogue.get("text"):
                translated.append(dialogue)
                continue

            if result_index < len(results):
                result = results[result_index]
                result_index += 1

                updated = dialogue.copy()
                updated["translated_text"] = result.translated_text
                updated["translation_confidence"] = result.confidence
                updated["used_translation_memory"] = result.used_memory

                translated.append(updated)
            else:
                translated.append(dialogue)

        return translated

    def _collect_statistics(self, results: List[TranslationResult]) -> Dict:
        """Collect translation statistics."""
        total = len(results)
        memory_hits = sum(1 for r in results if r.used_memory)
        avg_confidence = sum(r.confidence for r in results) / total if total > 0 else 0

        return {
            "total_translations": total,
            "memory_hits": memory_hits,
            "memory_hit_rate": memory_hits / total if total > 0 else 0,
            "average_confidence": avg_confidence,
            "translation_memory_stats": self.translation_memory.get_statistics(),
        }

    async def cleanup(self):
        """Cleanup resources."""
        if hasattr(self.engine, "_close"):
            await self.engine._close()
