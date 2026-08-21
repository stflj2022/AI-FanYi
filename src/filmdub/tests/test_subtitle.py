"""
Module 03 单元测试
"""

import unittest
import tempfile
import json
from pathlib import Path
from datetime import datetime

try:
    from filmdub.workers.subtitle import SubtitleConfig, TranslationMode
    from filmdub.workers.subtitle.models import SubtitleSource, Dialogue, SubtitleSourceType
    from filmdub.workers.subtitle.discovery import SubtitleScanner, SubtitleMatcher
    from filmdub.workers.subtitle.importer import SubtitleParser, DialogueNormalizer
    from filmdub.workers.subtitle.validator import SubtitleValidator, ValidationSeverity
    from filmdub.workers.subtitle.alignment import SubtitleAligner
    from filmdub.workers.subtitle.extractor import DialogueExtractor, DialogueType
except ImportError:
    from filmdub.workers.subtitle import SubtitleConfig, TranslationMode
    from filmdub.workers.subtitle.models import SubtitleSource, Dialogue, SubtitleSourceType
    from filmdub.workers.subtitle.discovery import SubtitleScanner, SubtitleMatcher
    from filmdub.workers.subtitle.importer import SubtitleParser, DialogueNormalizer
    from filmdub.workers.subtitle.validator import SubtitleValidator, ValidationSeverity
    from filmdub.workers.subtitle.alignment import SubtitleAligner
    from filmdub.workers.subtitle.extractor import DialogueExtractor, DialogueType


class TestSubtitleConfig(unittest.TestCase):
    """测试字幕配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = SubtitleConfig()

        self.assertEqual(config.translation_mode, TranslationMode.AUTO)
        self.assertEqual(config.target_language, "zh-CN")
        self.assertEqual(config.min_subtitle_quality, 0.80)
        self.assertTrue(len(config.subtitle_search_paths) > 0)


class TestSubtitleModels(unittest.TestCase):
    """测试字幕模型"""

    def test_subtitle_source(self):
        """测试字幕来源模型"""
        source = SubtitleSource(
            id="sub_001",
            project_id="proj_test",
            media_id="media_001",
            language="zh-CN",
            source_type=SubtitleSourceType.EXTERNAL,
            path="/path/to/subtitle.srt",
            format="srt"
        )

        self.assertEqual(source.id, "sub_001")
        self.assertEqual(source.language, "zh-CN")
        self.assertEqual(source.source_type, SubtitleSourceType.EXTERNAL)

        # 测试序列化
        data = source.to_dict()
        self.assertIsInstance(data, dict)

        # 测试反序列化
        restored = SubtitleSource.from_dict(data)
        self.assertEqual(restored.id, source.id)
        self.assertEqual(restored.language, source.language)

    def test_dialogue(self):
        """测试对话模型"""
        dialogue = Dialogue(
            id="dlg_000001",
            episode_id="S01E01",
            start=12.42,
            end=15.83,
            source_text="What are you doing?",
            normalized_text="What are you doing?",
            translated_text="你在干什么？"
        )

        self.assertEqual(dialogue.id, "dlg_000001")
        self.assertEqual(dialogue.start, 12.42)
        self.assertEqual(dialogue.end, 15.83)
        self.assertEqual(dialogue.source_text, "What are you doing?")

        # 测试序列化
        data = dialogue.to_dict()
        self.assertIsInstance(data, dict)


class TestDialogueNormalizer(unittest.TestCase):
    """测试对话标准化器"""

    def setUp(self):
        self.normalizer = DialogueNormalizer()

    def test_normalize_quotes(self):
        """测试引号标准化"""
        result = self.normalizer.normalize('"Hello"')
        self.assertIn('"', result.normalized_text)

    def test_normalize_whitespace(self):
        """测试空白标准化"""
        result = self.normalizer.normalize("Hello   world\n\n")
        self.assertEqual(result.normalized_text, "Hello world.")

    def test_extract_emotion_hint(self):
        """测试情感提示提取"""
        text = "[crying] I can't do this."
        cleaned, emotion = self.normalizer.extract_emotion_hint(text)
        self.assertEqual(emotion, "crying")
        self.assertEqual(cleaned, "I can't do this.")

    def test_extract_speaker_hint(self):
        """测试说话人提示提取"""
        text = "Walter: What are you doing?"
        cleaned, speaker = self.normalizer.extract_speaker_hint(text)
        self.assertEqual(speaker, "Walter")
        self.assertEqual(cleaned, "What are you doing?")


class TestSubtitleParser(unittest.TestCase):
    """测试字幕解析器"""

    def setUp(self):
        self.parser = SubtitleParser()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_parse_srt(self):
        """测试SRT解析"""
        # 创建测试SRT文件
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Hello, world!

2
00:00:04,000 --> 00:00:06,000
This is a test.
"""

        srt_path = Path(self.temp_dir) / "test.srt"
        srt_path.write_text(srt_content, encoding='utf-8')

        # 解析
        entries = self.parser.parse(srt_path)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].text, "Hello, world!")
        self.assertEqual(entries[1].text, "This is a test.")

    def test_to_jsonl(self):
        """测试导出为JSONL"""
        from filmdub.workers.subtitle.importer.parser import SubtitleEntry

        entries = [
            SubtitleEntry(index=0, start=1.0, end=3.0, text="Hello"),
            SubtitleEntry(index=1, start=4.0, end=6.0, text="World")
        ]

        jsonl_path = Path(self.temp_dir) / "test.jsonl"
        self.parser.to_jsonl(entries, jsonl_path, "en")

        # 验证文件存在
        self.assertTrue(jsonl_path.exists())

        # 验证内容
        lines = jsonl_path.read_text(encoding='utf-8').strip().split('\n')
        self.assertEqual(len(lines), 2)

        # 验证JSON格式
        data = json.loads(lines[0])
        self.assertEqual(data['text'], 'Hello')
        self.assertEqual(data['language'], 'en')


class TestSubtitleValidator(unittest.TestCase):
    """测试字幕验证器"""

    def setUp(self):
        self.config = SubtitleConfig()
        self.validator = SubtitleValidator(self.config)

    def test_validate_valid_entries(self):
        """测试验证有效的字幕"""
        from filmdub.workers.subtitle.importer.parser import SubtitleEntry

        entries = [
            SubtitleEntry(index=0, start=1.0, end=3.0, text="Hello"),
            SubtitleEntry(index=1, start=4.0, end=6.0, text="World")
        ]

        report = self.validator.validate(entries)

        self.assertEqual(report.total_entries, 2)
        self.assertEqual(report.valid_entries, 2)
        self.assertEqual(report.error_count, 0)

    def test_validate_invalid_time(self):
        """测试验证无效时间"""
        from filmdub.workers.subtitle.importer.parser import SubtitleEntry

        entries = [
            SubtitleEntry(index=0, start=5.0, end=3.0, text="Invalid time")
        ]

        report = self.validator.validate(entries)

        self.assertGreater(report.error_count, 0)
        self.assertTrue(any(i.issue_type == "invalid_time" for i in report.issues))

    def test_validate_empty_text(self):
        """测试验证空文本"""
        from filmdub.workers.subtitle.importer.parser import SubtitleEntry

        entries = [
            SubtitleEntry(index=0, start=1.0, end=3.0, text="")
        ]

        report = self.validator.validate(entries)

        self.assertGreater(report.error_count, 0)
        self.assertTrue(any(i.issue_type == "empty_text" for i in report.issues))


class TestSubtitleAligner(unittest.TestCase):
    """测试字幕对齐器"""

    def setUp(self):
        self.config = SubtitleConfig()
        self.aligner = SubtitleAligner(self.config)

    def test_align_no_offset_needed(self):
        """测试不需要偏移的对齐"""
        from filmdub.workers.subtitle.importer.parser import SubtitleEntry

        entries = [
            SubtitleEntry(index=0, start=1.0, end=3.0, text="Hello"),
            SubtitleEntry(index=1, start=4.0, end=6.0, text="World")
        ]

        result = self.aligner.align(entries, video_duration=3600.0)

        self.assertEqual(result.method, "none")
        self.assertEqual(result.offset, 0.0)
        self.assertEqual(result.scale, 1.0)

    def test_align_with_scaling(self):
        """测试需要缩放的对齐"""
        from filmdub.workers.subtitle.importer.parser import SubtitleEntry

        entries = [
            SubtitleEntry(index=0, start=1.0, end=3.0, text="Hello"),
            SubtitleEntry(index=1, start=4.0, end=6.0, text="World")
        ]

        # 字幕时长只有6秒，视频3600秒，需要缩放
        result = self.aligner.align(entries, video_duration=3600.0)

        # 由于时长差异超过阈值，应该应用缩放
        self.assertEqual(result.method, "scaling")


class TestDialogueExtractor(unittest.TestCase):
    """测试对话提取器"""

    def setUp(self):
        self.config = SubtitleConfig()
        self.extractor = DialogueExtractor(self.config)

    def test_extract_dialogue(self):
        """测试提取对话"""
        from filmdub.workers.subtitle.importer.parser import SubtitleEntry

        entries = [
            SubtitleEntry(index=0, start=1.0, end=3.0, text="Hello, how are you?"),
            SubtitleEntry(index=1, start=4.0, end=6.0, text="I'm fine, thanks.")
        ]

        dialogues = self.extractor.extract(entries)

        self.assertEqual(len(dialogues), 2)
        self.assertEqual(dialogues[0].dialogue_type, DialogueType.DIALOGUE)

    def test_extract_music(self):
        """测试识别音乐"""
        from filmdub.workers.subtitle.importer.parser import SubtitleEntry

        entries = [
            SubtitleEntry(index=0, start=1.0, end=3.0, text="♪ La la la ♪")
        ]

        dialogues = self.extractor.extract(entries)

        self.assertEqual(len(dialogues), 1)
        self.assertEqual(dialogues[0].dialogue_type, DialogueType.MUSIC)

    def test_filter_dialogues(self):
        """测试过滤对话"""
        from filmdub.workers.subtitle.importer.parser import SubtitleEntry

        entries = [
            SubtitleEntry(index=0, start=1.0, end=3.0, text="Hello"),
            SubtitleEntry(index=1, start=4.0, end=6.0, text="♪ Music ♪")
        ]

        dialogues = self.extractor.extract(entries)
        filtered = self.extractor.filter_dialogues(
            dialogues,
            include_types=[DialogueType.DIALOGUE]
        )

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].dialogue_type, DialogueType.DIALOGUE)


class TestSubtitleMatcher(unittest.TestCase):
    """测试字幕匹配器"""

    def setUp(self):
        self.config = SubtitleConfig()
        self.matcher = SubtitleMatcher(self.config)

    def test_match_perfect_filename(self):
        """测试完美文件名匹配"""
        from filmdub.workers.subtitle.discovery.scanner import ExternalSubtitle, SubtitleFormat

        subtitle = ExternalSubtitle(
            path=Path("Breaking.Bad.S01E01.chi.srt"),
            format=SubtitleFormat.SRT,
            language="zh-CN",
            size=1024
        )

        result = self.matcher.match_subtitle_to_video(
            subtitle,
            Path("Breaking.Bad.S01E01.mkv"),
            video_duration=3600.0,
            episode_info={"title": "Breaking Bad", "season": 1, "episode": 1}
        )

        # 应该有很高的分数
        self.assertGreater(result.score, 0.8)

    def test_find_best_subtitle(self):
        """测试找到最佳字幕"""
        from filmdub.workers.subtitle.discovery.scanner import ExternalSubtitle, SubtitleFormat

        subtitles = [
            ExternalSubtitle(
                path=Path("Breaking.Bad.S01E01.chi.srt"),
                format=SubtitleFormat.SRT,
                language="zh-CN",
                size=1024
            ),
            ExternalSubtitle(
                path=Path("some.other.show.srt"),
                format=SubtitleFormat.SRT,
                language="en",
                size=1024
            )
        ]

        best = self.matcher.find_best_subtitle(
            subtitles,
            Path("Breaking.Bad.S01E01.mkv"),
            video_duration=3600.0,
            episode_info={"title": "Breaking Bad", "season": 1, "episode": 1}
        )

        self.assertIsNotNone(best)
        # 第一个字幕应该被选中
        self.assertIn("Breaking", best.subtitle.path.name)


if __name__ == '__main__':
    unittest.main()
