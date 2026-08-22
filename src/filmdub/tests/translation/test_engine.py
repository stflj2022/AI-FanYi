"""Translation engine tests."""

import pytest

from filmdub.workers.translation.config import TranslationConfig
from filmdub.workers.translation.engine import MockTranslationEngine, QwenTranslationEngine
from filmdub.workers.translation.models import TranslationRequest


class TestMockTranslationEngine:
    """Test mock translation engine."""

    @pytest.mark.asyncio
    async def test_translate_single(self):
        """Test translating a single text."""
        engine = MockTranslationEngine()
        request = TranslationRequest(text="Hello, world!", source_lang="en", target_lang="zh")

        result = await engine.translate(request)

        assert result.original_text == "Hello, world!"
        assert "[翻译]" in result.translated_text
        assert "[/翻译]" in result.translated_text
        assert result.source_lang == "en"
        assert result.target_lang == "zh"
        assert result.confidence == 1.0
        assert result.used_memory is False

    @pytest.mark.asyncio
    async def test_batch_translate(self):
        """Test batch translation."""
        engine = MockTranslationEngine()
        requests = [
            TranslationRequest(text=f"Text {i}", source_lang="en", target_lang="zh")
            for i in range(5)
        ]

        results = await engine.batch_translate(requests)

        assert len(results) == 5
        for i, result in enumerate(results):
            assert f"Text {i}" in result.original_text
            assert "[翻译]" in result.translated_text


class TestQwenTranslationEngine:
    """Test Qwen translation engine."""

    def test_init(self):
        """Test engine initialization."""
        config = TranslationConfig(
            qwen_api_url="http://localhost:8000/v1/chat/completions",
            qwen_api_key="test-key",
        )
        engine = QwenTranslationEngine(config)

        assert engine.config.qwen_api_url == "http://localhost:8000/v1/chat/completions"
        assert engine.config.qwen_api_key == "test-key"

    def test_lang_name(self):
        """Test language name mapping."""
        engine = QwenTranslationEngine()

        assert engine._lang_name("en") == "英文"
        assert engine._lang_name("zh") == "中文"
        assert engine._lang_name("ja") == "日文"
        assert engine._lang_name("unknown") == "unknown"

    def test_build_prompt(self):
        """Test prompt building."""
        engine = QwenTranslationEngine()
        prompt = engine._build_prompt(
            text="Hello",
            source_lang="en",
            target_lang="zh",
            context="greeting",
            character="John",
            emotion="happy",
        )

        assert "英文" in prompt
        assert "中文" in prompt
        assert "Hello" in prompt
        assert "greeting" in prompt
        assert "John" in prompt
        assert "happy" in prompt

    def test_extract_translation(self):
        """Test translation extraction from response."""
        engine = QwenTranslationEngine()

        # Test simple translation
        assert engine._extract_translation("你好") == "你好"

        # Test with explanation prefix (strip the prefix)
        text = "翻译：你好"
        assert engine._extract_translation(text) == "你好"

        # Test with explanation line (skip entire line)
        text = "注：这是问候语"
        assert engine._extract_translation(text) == "注：这是问候语"  # No translation to extract

        # Test mixed: translation line + explanation line
        text = "翻译：你好\n注：这是问候语"
        assert engine._extract_translation(text) == "你好"  # Only keep translation

        # Test with numbered list (all numbered lines are explanations, skip them)
        # When all lines are skipped, return original text as fallback
        text = "1. 你好\n2. 世界"
        result = engine._extract_translation(text)
        assert result == text  # Fallback to original when nothing extracted

    @pytest.mark.asyncio
    async def test_translate_with_mock_api_error(self, mocker):
        """Test translation with API error."""
        config = TranslationConfig(
            qwen_api_url="http://localhost:9999/nonexistent",
            qwen_api_key="test",
        )
        engine = QwenTranslationEngine(config)

        request = TranslationRequest(text="Hello", source_lang="en", target_lang="zh")

        with pytest.raises(RuntimeError, match="Translation failed"):
            await engine.translate(request)
