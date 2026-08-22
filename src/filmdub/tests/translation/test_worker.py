"""M06 Worker tests."""

import pytest
from uuid import uuid4

from filmdub.workers.translation.config import TranslationConfig
from filmdub.workers.translation.engine import MockTranslationEngine
from filmdub.workers.translation.models import M06Input, TranslationRequest
from filmdub.workers.translation.worker import M06Worker


class TestM06Worker:
    """Test M06 Translation Worker."""

    def test_init_default_engine(self):
        """Test initialization with default engine."""
        worker = M06Worker()

        assert worker.config is not None
        assert worker.engine is not None
        assert worker.translation_memory is not None

    def test_init_custom_engine(self):
        """Test initialization with custom engine."""
        mock_engine = MockTranslationEngine()
        worker = M06Worker(engine=mock_engine)

        assert worker.engine is mock_engine

    @pytest.mark.asyncio
    async def test_process_simple_dialogue(self):
        """Test processing a simple dialogue."""
        worker = M06Worker()

        input_data = M06Input(
            project_id=uuid4(),
            job_id=uuid4(),
            dialogue_timeline=[
                {"text": "Hello", "speaker": "S01"},
                {"text": "How are you?", "speaker": "S02"},
            ],
            character_database={"characters": []},
        )

        output = await worker.process(input_data)

        assert output.project_id == input_data.project_id
        assert output.job_id == input_data.job_id
        assert len(output.translated_dialogues) == 2
        assert "translated_text" in output.translated_dialogues[0]
        assert "translated_text" in output.translated_dialogues[1]
        assert output.statistics["total_translations"] == 2

    @pytest.mark.asyncio
    async def test_process_with_character_info(self):
        """Test processing with character information."""
        worker = M06Worker()

        character_id = uuid4()
        input_data = M06Input(
            project_id=uuid4(),
            job_id=uuid4(),
            dialogue_timeline=[
                {
                    "text": "Hello",
                    "speaker": "S01",
                    "character_id": str(character_id),
                    "emotion": "happy",
                }
            ],
            character_database={
                "characters": [
                    {"id": str(character_id), "name": "John"}
                ]
            },
        )

        output = await worker.process(input_data)

        assert len(output.translated_dialogues) == 1
        assert "translated_text" in output.translated_dialogues[0]

    @pytest.mark.asyncio
    async def test_process_empty_text(self):
        """Test processing dialogues with empty text."""
        worker = M06Worker()

        input_data = M06Input(
            project_id=uuid4(),
            job_id=uuid4(),
            dialogue_timeline=[
                {"text": "Hello"},
                {"text": ""},  # Empty text
                {"text": "World"},
            ],
            character_database={"characters": []},
        )

        output = await worker.process(input_data)

        # Should only translate non-empty texts
        translated_count = sum(
            1 for d in output.translated_dialogues if d.get("translated_text")
        )
        assert translated_count == 2

    @pytest.mark.asyncio
    async def test_statistics_collection(self):
        """Test that statistics are collected correctly."""
        worker = M06Worker()

        input_data = M06Input(
            project_id=uuid4(),
            job_id=uuid4(),
            dialogue_timeline=[{"text": f"Text {i}"} for i in range(10)],
            character_database={"characters": []},
        )

        output = await worker.process(input_data)

        assert "total_translations" in output.statistics
        assert "memory_hits" in output.statistics
        assert "memory_hit_rate" in output.statistics
        assert "average_confidence" in output.statistics
        assert "translation_memory_stats" in output.statistics

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test worker cleanup."""
        mock_engine = MockTranslationEngine()
        worker = M06Worker(engine=mock_engine)

        # Should not raise
        await worker.cleanup()

    def test_prepare_requests(self):
        """Test preparing translation requests."""
        worker = M06Worker()

        dialogues = [
            {"text": "Hello", "speaker": "S01"},
            {"text": "Hi there", "speaker": "S02"},
        ]

        requests = worker._prepare_requests(dialogues, {"characters": []})

        assert len(requests) == 2
        assert requests[0].text == "Hello"
        assert requests[1].text == "Hi there"

    def test_build_context(self):
        """Test context building."""
        worker = M06Worker()

        dialogues = [
            {"text": "Line 1"},
            {"text": "Line 2"},
            {"text": "Line 3"},
            {"text": "Line 4"},
            {"text": "Line 5"},
        ]

        context = worker._build_context(dialogues, 2)  # Middle line

        # Should include previous and next lines
        assert "Line 1" in context or "Line 2" in context
        assert "Line 4" in context or "Line 5" in context
        assert "Line 3" not in context  # Current line not in context

    def test_get_character_name(self):
        """Test getting character name."""
        worker = M06Worker()

        character_id = str(uuid4())
        character_database = {
            "characters": [
                {"id": character_id, "name": "John Doe"}
            ]
        }

        name = worker._get_character_name(character_id, character_database)

        assert name == "John Doe"

        # Test non-existent character
        name = worker._get_character_name("nonexistent", character_database)
        assert name is None
