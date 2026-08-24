"""
M13 QA 增强功能测试（ticket-033）

覆盖：响度检测（LUFS/峰值）、静音检测、爆音检测（峰值阈值）、
漏台词/重复台词检测、人物错配检测、QA 报告文件输出。
"""
import json
import os
import pytest

from filmdub.workers.qa import (
    M13Config,
    QAChecker,
    QAIssueCategory,
    QAIssueSeverity,
)
from filmdub.workers.qa.models import (
    TechnicalQuality,
    VoiceQuality,
    QAResult,
)


class TestLoudnessParsing:
    """响度/峰值解析测试"""

    EBUR128_OUTPUT = """\
[Parsed_ebur128_0 @ 0x1] Summary:
  Integrated loudness:
    I: -22.8 LUFS
    Threshold: -32.8 LUFS
  Loudness range:
    LRA: 4.3 LU
  True peak:
    Peak: -1.2 dBFS
"""

    VOLUMEDETECT_OUTPUT = """\
[Parsed_volumedetect_0 @ 0x2] mean_volume: -17.3 dB
[Parsed_volumedetect_0 @ 0x2] max_volume: -0.5 dB
[Parsed_volumedetect_0 @ 0x2] histogram_0db: 12
"""

    @pytest.fixture
    def checker(self):
        return QAChecker(config=M13Config(report_enabled=False))

    def test_parse_ebur128_loudness(self, checker):
        assert checker._parse_ebur128_loudness(self.EBUR128_OUTPUT) == pytest.approx(-22.8)

    def test_parse_dbfs_peak(self, checker):
        assert checker._parse_dbfs_peak(self.EBUR128_OUTPUT) == pytest.approx(-1.2)

    def test_parse_volumedetect(self, checker):
        assert checker._parse_volumedetect(self.VOLUMEDETECT_OUTPUT, "mean_volume") == pytest.approx(-17.3)
        assert checker._parse_volumedetect(self.VOLUMEDETECT_OUTPUT, "max_volume") == pytest.approx(-0.5)

    def test_parse_invalid(self, checker):
        assert checker._parse_ebur128_loudness("no data here") is None
        assert checker._parse_dbfs_peak("no data here") is None
        assert checker._parse_volumedetect("no data here", "max_volume") is None


class TestLoudnessCheck:
    """响度检测测试（mock ffmpeg 输出）"""

    @pytest.fixture
    def checker(self):
        return QAChecker(config=M13Config(report_enabled=False))

    def test_check_loudness_ebur128(self, checker, monkeypatch):
        output = """\
[Parsed_ebur128_0] Summary:
  Integrated loudness:
    I: -23.1 LUFS
  True peak:
    Peak: -1.0 dBFS
"""
        monkeypatch.setattr(checker, "_run_ffmpeg_capture", lambda cmd: output)
        loudness, peak = checker._check_loudness("fake.mp4")
        assert loudness == pytest.approx(-23.1)
        assert peak == pytest.approx(-1.0)

    def test_check_loudness_fallback_volumedetect(self, checker, monkeypatch):
        # 第一次（ebur128）返回空，第二次（volumedetect）返回数据
        outputs = [
            "",
            """\
[Parsed_volumedetect_0] mean_volume: -18.0 dB
[Parsed_volumedetect_0] max_volume: -0.3 dB
""",
        ]
        monkeypatch.setattr(checker, "_run_ffmpeg_capture", lambda cmd: outputs.pop(0))
        loudness, peak = checker._check_loudness("fake.mp4")
        assert loudness == pytest.approx(-18.0)
        assert peak == pytest.approx(-0.3)

    def test_check_loudness_failed(self, checker, monkeypatch):
        monkeypatch.setattr(checker, "_run_ffmpeg_capture", lambda cmd: None)
        loudness, peak = checker._check_loudness("fake.mp4")
        assert loudness is None
        assert peak is None


class TestSilenceCheck:
    """静音检测测试"""

    @pytest.fixture
    def checker(self):
        return QAChecker(config=M13Config(report_enabled=False))

    def test_check_silence_detects_segments(self, checker, monkeypatch):
        output = """\
[silencedetect @ 0x3] silence_start: 2.0
[silencedetect @ 0x3] silence_end: 5.5 | silence_duration: 3.5
[silencedetect @ 0x3] silence_start: 10.0
[silencedetect @ 0x3] silence_end: 10.8 | silence_duration: 0.8
"""
        monkeypatch.setattr(checker, "_run_ffmpeg_capture", lambda cmd: output)
        issues = checker._check_silence("fake.mp4")
        # 仅第一个静音段（3.5s）达到阈值（默认 2s）
        assert len(issues) == 1
        assert issues[0].category == QAIssueCategory.TECHNICAL
        assert issues[0].timestamp == pytest.approx(2.0)
        assert issues[0].duration == pytest.approx(3.5)

    def test_check_silence_no_output(self, checker, monkeypatch):
        monkeypatch.setattr(checker, "_run_ffmpeg_capture", lambda cmd: "")
        assert checker._check_silence("fake.mp4") == []

    def test_check_silence_failed(self, checker, monkeypatch):
        monkeypatch.setattr(checker, "_run_ffmpeg_capture", lambda cmd: None)
        assert checker._check_silence("fake.mp4") == []


class TestMissingDuplicateDialogue:
    """漏台词/重复台词检测测试"""

    @pytest.fixture
    def checker(self):
        return QAChecker(config=M13Config(report_enabled=False))

    def test_missing_dialogue(self, checker):
        dialogues = [
            {"id": "1", "text": "正常对白", "start_time": 0.0, "end_time": 1.0},
            {"id": "2", "text": "", "start_time": 1.0, "end_time": 2.0},
            {"id": "3", "text": None, "start_time": 2.0, "end_time": 3.0},
        ]
        score, issues = checker._check_missing_duplicate_dialogue(dialogues)
        assert score < 100.0
        assert any("漏台词" in i.title for i in issues)
        assert issues[0].severity == QAIssueSeverity.HIGH

    def test_duplicate_dialogue(self, checker):
        dialogues = [
            {"id": "1", "text": "重复的话", "start_time": 0.0, "end_time": 1.0},
            {"id": "2", "text": "重复的话", "start_time": 0.3, "end_time": 1.3},
        ]
        score, issues = checker._check_missing_duplicate_dialogue(dialogues)
        assert score < 100.0
        assert any("重复台词" in i.title for i in issues)

    def test_no_problem(self, checker):
        dialogues = [
            {"id": "1", "text": "第一句", "start_time": 0.0, "end_time": 1.0},
            {"id": "2", "text": "第二句", "start_time": 2.0, "end_time": 3.0},
        ]
        score, issues = checker._check_missing_duplicate_dialogue(dialogues)
        assert score == 100.0
        assert issues == []

    def test_empty_dialogues(self, checker):
        score, issues = checker._check_missing_duplicate_dialogue([])
        assert score == 100.0
        assert issues == []


class TestCharacterMismatch:
    """人物错配检测测试"""

    @pytest.fixture
    def checker(self):
        return QAChecker(config=M13Config(report_enabled=False))

    def test_mismatch(self, checker, tmp_path):
        character_db = tmp_path / "db.json"
        character_db.write_text(json.dumps({
            "characters": {
                "char1": {"id": "char1", "name": "Walter White"},
                "char2": {"id": "char2", "name": "Jesse Pinkman"},
            }
        }), encoding="utf-8")
        dialogues = [
            {"character_id": "char1", "speaker_id": "char2", "start_time": 0.0},
            {"character_id": "char1", "speaker_id": "char1", "start_time": 1.0},
        ]
        score, issues = checker._check_character_mismatch(dialogues, str(character_db))
        assert score < 100.0
        assert any("人物错配" in i.title for i in issues)
        assert issues[0].severity == QAIssueSeverity.HIGH

    def test_all_match(self, checker):
        dialogues = [
            {"character_id": "char1", "speaker_id": "char1", "start_time": 0.0},
            {"character_id": "char2", "speaker_id": "char2", "start_time": 1.0},
        ]
        score, issues = checker._check_character_mismatch(dialogues, None)
        assert score == 100.0
        assert not any("人物错配" in i.title for i in issues)

    def test_missing_speaker_info(self, checker):
        dialogues = [
            {"character_id": "char1", "start_time": 0.0},
        ]
        score, issues = checker._check_character_mismatch(dialogues, None)
        # 缺少说话人信息不惩罚
        assert score == 100.0
        assert any("缺少说话人信息" in i.title for i in issues)
        assert issues[0].severity == QAIssueSeverity.INFO


class TestQaReport:
    """QA 报告文件输出测试"""

    def test_write_report(self, tmp_path):
        config = M13Config(report_enabled=True, output_dir=str(tmp_path))
        checker = QAChecker(config=config)
        result = QAResult(
            success=True,
            overall_score=88.0,
            video_file="/tmp/示例视频.mp4",
            technical_quality=TechnicalQuality(
                passed=True, score=90.0, duration=10.0, size_bytes=1000,
                loudness_lufs=-23.0, peak_db=-1.0,
            ),
            voice_quality=VoiceQuality(passed=True, score=86.0),
            issues=[],
        )
        path = checker._write_report(result)
        assert path is not None
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["overall_score"] == pytest.approx(88.0)
        assert data["technical_quality"]["loudness_lufs"] == pytest.approx(-23.0)
        assert data["technical_quality"]["peak_db"] == pytest.approx(-1.0)
        assert data["video_file"] == "/tmp/示例视频.mp4"

    def test_write_report_disabled(self, tmp_path):
        config = M13Config(report_enabled=False, output_dir=str(tmp_path))
        checker = QAChecker(config=config)
        result = QAResult(
            success=True,
            overall_score=88.0,
            video_file="test.mp4",
            technical_quality=TechnicalQuality(passed=True, score=90.0, duration=0.0, size_bytes=0),
            voice_quality=VoiceQuality(passed=True, score=86.0),
            issues=[],
        )
        assert checker._write_report(result) is None
