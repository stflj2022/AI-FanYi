"""Translation engine base class and implementations."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import httpx

from .config import TranslationConfig, get_config
from .models import TranslationRequest, TranslationResult

logger = logging.getLogger(__name__)


class TranslationEngine(ABC):
    """Base class for translation engines."""

    def __init__(self, config: Optional[TranslationConfig] = None):
        """Initialize translation engine."""
        self.config = config or get_config()

    @abstractmethod
    async def translate(self, request: TranslationRequest) -> TranslationResult:
        """Translate a single text."""

    @abstractmethod
    async def batch_translate(
        self, requests: List[TranslationRequest]
    ) -> List[TranslationResult]:
        """Translate multiple texts in batch."""

    async def translate_with_context(
        self,
        request: TranslationRequest,
        previous_context: List[str],
        next_context: List[str],
    ) -> TranslationResult:
        """Translate with context from previous and next lines."""
        # Default implementation just calls translate
        return await self.translate(request)


class QwenTranslationEngine(TranslationEngine):
    """Qwen-based translation engine."""

    def __init__(self, config: Optional[TranslationConfig] = None):
        """Initialize Qwen translation engine."""
        super().__init__(config)
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(timeout=60.0)
        return self.client

    async def _close(self):
        """Close HTTP client."""
        if self.client and not self.client.is_closed:
            await self.client.aclose()

    def _build_prompt(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
        character: Optional[str] = None,
        emotion: Optional[str] = None,
    ) -> str:
        """Build translation prompt for Qwen."""
        prompt_parts = [
            f"请将以下{self._lang_name(source_lang)}文本翻译成{self._lang_name(target_lang)}：",
            "",
        ]

        if context:
            prompt_parts.append(f"上下文：{context}")
            prompt_parts.append("")

        if character:
            prompt_parts.append(f"说话人：{character}")
            prompt_parts.append("")

        if emotion:
            prompt_parts.append(f"情绪：{emotion}")
            prompt_parts.append("")

        prompt_parts.append(f"原文：{text}")
        prompt_parts.append("")
        prompt_parts.append("要求：")
        prompt_parts.append("1. 翻译要符合中文表达习惯")
        prompt_parts.append("2. 保持原句的语气和情绪")
        prompt_parts.append("3. 专有名词和人名要保持一致")
        prompt_parts.append("4. 只输出翻译结果，不要解释")

        return "\n".join(prompt_parts)

    def _lang_name(self, lang_code: str) -> str:
        """Get language name from code."""
        lang_names = {
            "en": "英文",
            "zh": "中文",
            "ja": "日文",
            "ko": "韩文",
            "fr": "法文",
            "de": "德文",
            "es": "西班牙文",
        }
        return lang_names.get(lang_code, lang_code)

    async def translate(self, request: TranslationRequest) -> TranslationResult:
        """Translate a single text using Qwen."""
        client = await self._get_client()

        character_name = None
        if request.character_id:
            # TODO: Look up character name from database
            character_name = str(request.character_id)

        prompt = self._build_prompt(
            text=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            context=request.context,
            character=character_name,
            emotion=request.emotion,
        )

        try:
            response = await client.post(
                self.config.qwen_api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.config.qwen_api_key}",
                },
                json={
                    "model": self.config.qwen_model_path or "qwen",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.config.qwen_temperature,
                    "max_tokens": self.config.qwen_max_tokens,
                },
            )
            response.raise_for_status()

            data = response.json()
            translated_text = data["choices"][0]["message"]["content"].strip()

            # Extract just the translation (remove any explanations)
            translated_text = self._extract_translation(translated_text)

            return TranslationResult(
                original_text=request.text,
                translated_text=translated_text,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                confidence=0.9,  # Qwen generally produces good translations
                used_memory=False,
            )

        except httpx.HTTPError as e:
            logger.error(f"Translation API error: {e}")
            raise RuntimeError(f"Translation failed: {e}") from e
        except (KeyError, IndexError) as e:
            logger.error(f"Invalid API response: {e}")
            raise RuntimeError(f"Invalid API response: {e}") from e

    def _extract_translation(self, text: str) -> str:
        """Extract translation from response, removing any explanations."""
        # Remove common patterns of explanations
        lines = text.split("\n")
        translation_lines = []

        # Prefixes that indicate the line contains the translation (strip the prefix)
        translation_prefixes = ["翻译：", "译文：", "结果："]
        # Prefixes that indicate the line is an explanation (skip the entire line)
        explanation_prefixes = ["Note:", "注：", "解释：", "说明："]
        # Prefixes that indicate numbered lists (skip)
        number_prefixes = [f"{i}." for i in range(1, 21)]

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Check if this is a translation line with prefix
            for prefix in translation_prefixes:
                if line_stripped.startswith(prefix):
                    # Strip the prefix and keep the rest
                    translation_lines.append(line_stripped[len(prefix):].strip())
                    break
            else:
                # Check if this is an explanation line (skip)
                if line_stripped.startswith(tuple(explanation_prefixes + number_prefixes)):
                    continue
                # Keep the line as-is
                translation_lines.append(line_stripped)

        result = "\n".join(translation_lines).strip()
        return result if result else text

    async def batch_translate(
        self, requests: List[TranslationRequest]
    ) -> List[TranslationResult]:
        """Translate multiple texts in batch."""
        # Process in parallel with concurrency limit
        semaphore = asyncio.Semaphore(self.config.batch_size)

        async def translate_with_semaphore(req: TranslationRequest) -> TranslationResult:
            async with semaphore:
                return await self.translate(req)

        tasks = [translate_with_semaphore(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Translation failed for request {i}: {result}")
                final_results.append(
                    TranslationResult(
                        original_text=requests[i].text,
                        translated_text=requests[i].text,  # Fallback to original
                        source_lang=requests[i].source_lang,
                        target_lang=requests[i].target_lang,
                        confidence=0.0,
                        used_memory=False,
                    )
                )
            else:
                final_results.append(result)

        return final_results


class MockTranslationEngine(TranslationEngine):
    """Mock translation engine for testing."""

    async def translate(self, request: TranslationRequest) -> TranslationResult:
        """Mock translate - just returns the original text."""
        await asyncio.sleep(0.01)
        return TranslationResult(
            original_text=request.text,
            translated_text=f"[翻译]{request.text}[/翻译]",
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            confidence=1.0,
            used_memory=False,
        )

    async def batch_translate(
        self, requests: List[TranslationRequest]
    ) -> List[TranslationResult]:
        """Mock batch translate."""
        return await asyncio.gather(*[self.translate(req) for req in requests])
