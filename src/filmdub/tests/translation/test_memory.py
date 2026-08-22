"""Translation memory tests."""

import json
import tempfile
from pathlib import Path

import pytest

from filmdub.workers.translation.memory import TranslationMemory
from filmdub.workers.translation.models import TranslationMemoryEntry


class TestTranslationMemory:
    """Test translation memory."""

    def test_init_creates_file(self):
        """Test that initialization creates file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"
            memory = TranslationMemory(str(path))

            assert path.exists()
            assert isinstance(memory.entries, list)
            assert isinstance(memory.glossary, list)

    def test_add_and_find_translation(self):
        """Test adding and finding translations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"
            memory = TranslationMemory(str(path))

            # Add a translation
            entry = memory.add_translation(
                source_text="Hello",
                translated_text="你好",
                source_lang="en",
                target_lang="zh",
                context="greeting",
            )

            assert entry.source_text == "Hello"
            assert entry.translated_text == "你好"
            assert len(memory.entries) == 1

            # Find the translation
            found = memory.find_translation(
                source_text="Hello", source_lang="en", target_lang="zh"
            )

            assert found is not None
            assert found.translated_text == "你好"
            assert found.usage_count >= 1

    def test_find_with_similarity(self):
        """Test finding translations with similarity matching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"
            memory = TranslationMemory(str(path))

            # Add a translation
            memory.add_translation(
                source_text="Hello, world!",
                translated_text="你好，世界！",
                source_lang="en",
                target_lang="zh",
            )

            # Find similar text
            found = memory.find_translation(
                source_text="Hello world!",  # Slightly different
                source_lang="en",
                target_lang="zh",
                similarity_threshold=0.8,
            )

            assert found is not None
            assert found.translated_text == "你好，世界！"

    def test_find_no_match(self):
        """Test finding when no match exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"
            memory = TranslationMemory(str(path))

            # Try to find without adding
            found = memory.find_translation(
                source_text="Nonexistent", source_lang="en", target_lang="zh"
            )

            assert found is None

    def test_add_term(self):
        """Test adding glossary terms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"
            memory = TranslationMemory(str(path))

            term = memory.add_term(
                source_term="Walter",
                target_term="沃尔特",
                category="name",
                notes="Character name",
            )

            assert term.source_term == "Walter"
            assert term.target_term == "沃尔特"
            assert len(memory.glossary) == 1

    def test_find_term(self):
        """Test finding glossary terms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"
            memory = TranslationMemory(str(path))

            memory.add_term(source_term="Walter", target_term="沃尔特")

            found = memory.find_term("Walter")
            assert found is not None
            assert found.target_term == "沃尔特"

            not_found = memory.find_term("Nonexistent")
            assert not_found is None

    def test_apply_glossary(self):
        """Test applying glossary to text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"
            memory = TranslationMemory(str(path))

            memory.add_term(source_term="Walter", target_term="沃尔特")
            memory.add_term(source_term="Jesse", target_term="杰西")

            terms = memory.apply_glossary("Walter and Jesse are talking.")

            assert "Walter" in terms
            assert "Jesse" in terms
            assert terms["Walter"] == "沃尔特"
            assert terms["Jesse"] == "杰西"

    def test_get_statistics(self):
        """Test getting statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"
            memory = TranslationMemory(str(path))

            # Add some data
            memory.add_translation("Hello", "你好", "en", "zh")
            memory.add_translation("Goodbye", "再见", "en", "zh")
            memory.add_term("Walter", "沃尔特")

            stats = memory.get_statistics()

            assert stats["total_entries"] == 2
            assert stats["total_glossary_terms"] == 1
            assert len(stats["language_pairs"]) == 1
            assert stats["language_pairs"][0]["pair"] == "en->zh"

    def test_persistence(self):
        """Test that data persists across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"

            # Create and add data
            memory1 = TranslationMemory(str(path))
            memory1.add_translation("Hello", "你好", "en", "zh")

            # Create new instance and verify data
            memory2 = TranslationMemory(str(path))
            assert len(memory2.entries) == 1
            assert memory2.entries[0].source_text == "Hello"

    def test_load_invalid_json(self, caplog):
        """Test loading invalid JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "memory.json"

            # Write invalid JSON
            path.write_text("{ invalid json")

            # Should not crash, just log warning
            memory = TranslationMemory(str(path))
            assert len(memory.entries) == 0
