"""
M13 QA 模块测试
"""
import json
import os
import tempfile
import pytest
from pathlib import Path

from filmdub.workers.qa import (
    M13Config,
    QAChecker,
    QAInput,
    QAResult,
    QAIssue,
    QAIssueSeverity,
    QAIssueCategory,
)


class TestM13Config:
    """M13Config 测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = M13Config()
        assert config.ffprobe_path == "ffprobe"
        assert config.ffmpeg_path == "ffmpeg"
        assert config.min_video_width == 720
        assert config.min_video_height == 480
        assert config.target_lufs == -23.0
        assert config.sync_tolerance_seconds == 0.1

    def test_custom_config(self):
        """测试自定义配置"""
        config = M13Config(
            min_video_width=1280,
            min_video_height=720,
            target_lufs=-16.0,
            strict_mode=True
        )
        assert config.min_video_width == 1280
        assert config.min_video_height == 720
        assert config.target_lufs == -16.0
        assert config.strict_mode is True


class TestQAChecker:
    """QAChecker 测试"""

    @pytest.fixture
    def checker(self):
        """创建 QA 检查器"""
        return QAChecker()

    @pytest.fixture
    def sample_video(self):
        """创建测试视频文件（模拟）"""
        # 注意：实际测试需要真实视频文件
        # 这里只是标记测试需要视频文件
        return "测试视频/laobai.mp4"

    @pytest.fixture
    def sample_dialogue_timeline(self, tmp_path):
        """创建示例对白时间轴"""
        dialogues = [
            {
                "id": "1",
                "character_id": "char1",
                "voice_id": "voice1",
                "text": "你好，我是 Walter。",
                "start_time": 0.0,
                "end_time": 2.5,
                "emotion": "neutral"
            },
            {
                "id": "2",
                "character_id": "char1",
                "voice_id": "voice1",
                "text": "这是一段测试对白。",
                "start_time": 3.0,
                "end_time": 5.0,
                "emotion": "happy"
            },
            {
                "id": "3",
                "character_id": "char2",
                "voice_id": "voice2",
                "text": "你好，我是 Jesse。",
                "start_time": 5.5,
                "end_time": 7.5,
                "emotion": "neutral"
            }
        ]

        file_path = tmp_path / "dialogue_timeline.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dialogues, f, ensure_ascii=False, indent=2)

        return str(file_path)

    @pytest.fixture
    def sample_character_db(self, tmp_path):
        """创建示例人物数据库"""
        characters = {
            "char1": {
                "id": "char1",
                "name": "Walter White",
                "voice_id": "voice1"
            },
            "char2": {
                "id": "char2",
                "name": "Jesse Pinkman",
                "voice_id": "voice2"
            }
        }

        file_path = tmp_path / "character_db.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"characters": characters}, f, ensure_ascii=False, indent=2)

        return str(file_path)

    def test_health_check(self, checker):
        """测试健康检查"""
        result = checker.health_check()
        # 如果系统安装了 ffprobe，应该返回 True
        # 否则返回 False
        assert isinstance(result, bool)

    def test_validate_input_missing_file(self, checker):
        """测试验证输入 - 文件不存在"""
        with pytest.raises(FileNotFoundError):
            input_data = QAInput(video_file="/nonexistent/video.mp4")
            checker._validate_input(input_data)

    def test_check_voice_consistency(self, checker, sample_dialogue_timeline, sample_character_db):
        """测试音色一致性检查"""
        with open(sample_dialogue_timeline, 'r', encoding='utf-8') as f:
            dialogues = json.load(f)

        score, issues = checker._check_voice_consistency(dialogues, sample_character_db)

        assert 0.0 <= score <= 100.0
        assert isinstance(issues, list)

        # 所有人物使用一致的音色，不应该有问题
        assert score == 100.0
        assert len(issues) == 0

    def test_check_voice_consistency_with_inconsistency(self, checker, tmp_path):
        """测试音色不一致的情况"""
        dialogues = [
            {
                "id": "1",
                "character_id": "char1",
                "voice_id": "voice1",
                "text": "你好。",
                "start_time": 0.0,
                "end_time": 1.0
            },
            {
                "id": "2",
                "character_id": "char1",
                "voice_id": "voice2",  # 同一人物使用不同音色
                "text": "你好。",
                "start_time": 1.0,
                "end_time": 2.0
            }
        ]

        score, issues = checker._check_voice_consistency(dialogues, None)

        # 应该检测到音色不一致
        assert score < 100.0
        assert len(issues) > 0
        assert issues[0].category == QAIssueCategory.VOICE
        assert issues[0].severity == QAIssueSeverity.HIGH
        assert "音色不一致" in issues[0].title

    def test_check_emotion_match(self, checker, sample_dialogue_timeline):
        """测试情绪匹配检查"""
        with open(sample_dialogue_timeline, 'r', encoding='utf-8') as f:
            dialogues = json.load(f)

        score, issues = checker._check_emotion_match(dialogues)

        assert 0.0 <= score <= 100.0
        assert isinstance(issues, list)

    def test_check_emotion_match_no_tags(self, checker):
        """测试没有情绪标签的情况"""
        dialogues = [
            {
                "id": "1",
                "text": "你好。",
                "start_time": 0.0,
                "end_time": 1.0
            }
        ]

        score, issues = checker._check_emotion_match(dialogues)

        # 应该提示缺少情绪标签
        assert score < 100.0
        assert len(issues) > 0
        assert issues[0].category == QAIssueCategory.VOICE
        assert "情绪标签" in issues[0].title

    def test_check_speech_rate(self, checker, sample_dialogue_timeline):
        """测试语速检查"""
        with open(sample_dialogue_timeline, 'r', encoding='utf-8') as f:
            dialogues = json.load(f)

        score, issues = checker._check_speech_rate(dialogues)

        assert 0.0 <= score <= 100.0
        assert isinstance(issues, list)

    def test_check_speech_rate_too_fast(self, checker):
        """测试语速过快"""
        dialogues = [
            {
                "id": "1",
                "text": "这是一段非常长的文本，应该在很短时间内说完。",
                "start_time": 0.0,
                "end_time": 0.5  # 只有 0.5 秒，但文本很长
            }
        ]

        score, issues = checker._check_speech_rate(dialogues)

        # 应该检测到语速过快
        assert score < 100.0
        assert len(issues) > 0
        assert issues[0].category == QAIssueCategory.VOICE
        assert "过快" in issues[0].title

    def test_check_speech_rate_too_slow(self, checker):
        """测试语速过慢"""
        dialogues = [
            {
                "id": "1",
                "text": "你。",
                "start_time": 0.0,
                "end_time": 10.0  # 10 秒只说一个字
            }
        ]

        score, issues = checker._check_speech_rate(dialogues)

        # 应该检测到语速过慢
        assert score < 100.0
        assert len(issues) > 0
        assert "过慢" in issues[0].title

    def test_check_translation_quality(self, checker, sample_dialogue_timeline):
        """测试翻译质量检查"""
        with open(sample_dialogue_timeline, 'r', encoding='utf-8') as f:
            dialogues = json.load(f)

        score, issues = checker._check_translation_quality(dialogues)

        assert 0.0 <= score <= 100.0
        assert isinstance(issues, list)

    def test_check_translation_quality_empty_text(self, checker):
        """测试空文本检查"""
        dialogues = [
            {
                "id": "1",
                "text": "",  # 空文本
                "start_time": 0.0,
                "end_time": 1.0
            }
        ]

        score, issues = checker._check_translation_quality(dialogues)

        # 应该检测到空文本
        assert score < 100.0
        assert len(issues) > 0
        assert issues[0].severity == QAIssueSeverity.HIGH
        assert "空文本" in issues[0].title

    def test_check_translation_quality_too_long(self, checker):
        """测试过长文本检查"""
        dialogues = [
            {
                "id": "1",
                "text": "A" * 250,  # 250 个字符
                "start_time": 0.0,
                "end_time": 10.0
            }
        ]

        score, issues = checker._check_translation_quality(dialogues)

        # 应该检测到过长文本
        assert score < 100.0
        assert len(issues) > 0
        assert "过长" in issues[0].title

    def test_parse_fps(self, checker):
        """测试帧率解析"""
        # 整数帧率
        assert checker._parse_fps("30") == 30.0

        # 分数帧率
        assert abs(checker._parse_fps("30000/1001") - 29.97) < 0.01

        # None
        assert checker._parse_fps(None) is None

        # 无效字符串
        assert checker._parse_fps("invalid") is None


class TestQAResult:
    """QAResult 测试"""

    def test_calculate_statistics(self):
        """测试统计计算"""
        from filmdub.workers.qa.models import TechnicalQuality, VoiceQuality

        result = QAResult(
            success=True,
            overall_score=85.0,
            video_file="test.mp4",
            technical_quality=TechnicalQuality(
                passed=True,
                score=80.0,
                duration=0.0,
                size_bytes=0
            ),
            voice_quality=VoiceQuality(
                passed=True,
                score=90.0
            ),
            issues=[
                QAIssue(
                    category=QAIssueCategory.TECHNICAL,
                    severity=QAIssueSeverity.CRITICAL,
                    title="Critical issue",
                    description="..."
                ),
                QAIssue(
                    category=QAIssueCategory.VOICE,
                    severity=QAIssueSeverity.HIGH,
                    title="High issue",
                    description="..."
                ),
                QAIssue(
                    category=QAIssueCategory.VOICE,
                    severity=QAIssueSeverity.MEDIUM,
                    title="Medium issue",
                    description="..."
                ),
                QAIssue(
                    category=QAIssueCategory.OTHER,
                    severity=QAIssueSeverity.LOW,
                    title="Low issue",
                    description="..."
                ),
                QAIssue(
                    category=QAIssueCategory.OTHER,
                    severity=QAIssueSeverity.INFO,
                    title="Info issue",
                    description="..."
                ),
            ]
        )

        result.calculate_statistics()

        assert result.critical_issues == 1
        assert result.high_issues == 1
        assert result.medium_issues == 1
        assert result.low_issues == 1
        assert result.info_issues == 1

    def test_calculate_overall_score(self):
        """测试总体评分计算"""
        from filmdub.workers.qa.models import TechnicalQuality, VoiceQuality

        result = QAResult(
            success=True,
            overall_score=0.0,
            video_file="test.mp4",
            technical_quality=TechnicalQuality(
                passed=True,
                score=80.0,
                duration=0.0,
                size_bytes=0
            ),
            voice_quality=VoiceQuality(
                passed=True,
                score=90.0
            ),
            issues=[]
        )

        result.calculate_overall_score()

        # 技术质量 40%，配音质量 60%
        # 80 * 0.4 + 90 * 0.6 = 86
        assert abs(result.overall_score - 86.0) < 0.1


@pytest.mark.integration
class TestQACheckerIntegration:
    """QA 检查器集成测试（需要实际视频文件）"""

    @pytest.fixture
    def checker(self):
        """创建 QA 检查器"""
        return QAChecker()

    @pytest.fixture
    def real_video(self):
        """真实视频文件路径"""
        video_path = "测试视频/laobai.mp4"
        if os.path.exists(video_path):
            return video_path
        pytest.skip(f"测试视频不存在: {video_path}")

    def test_full_qa_check(self, checker, real_video):
        """测试完整的 QA 检查流程"""
        input_data = QAInput(
            video_file=real_video
        )

        result = checker.check(input_data)

        assert isinstance(result, QAResult)
        assert result.video_file == real_video
        assert 0.0 <= result.overall_score <= 100.0
        assert isinstance(result.technical_quality, dict) or hasattr(result.technical_quality, 'passed')
        assert isinstance(result.voice_quality, dict) or hasattr(result.voice_quality, 'passed')
        assert isinstance(result.issues, list)

    def test_check_with_dialogue_timeline(self, checker, real_video, tmp_path):
        """测试带对白时间轴的 QA 检查"""
        # 创建对白时间轴
        dialogues = [
            {
                "id": "1",
                "character_id": "char1",
                "voice_id": "voice1",
                "text": "测试对白。",
                "start_time": 0.0,
                "end_time": 2.0,
                "emotion": "neutral"
            }
        ]

        dialogue_file = tmp_path / "dialogue.json"
        with open(dialogue_file, 'w', encoding='utf-8') as f:
            json.dump(dialogues, f, ensure_ascii=False, indent=2)

        input_data = QAInput(
            video_file=real_video,
            dialogue_timeline=str(dialogue_file)
        )

        result = checker.check(input_data)

        assert isinstance(result, QAResult)
        # 检查配音质量部分
        voice_quality = result.voice_quality
        assert hasattr(voice_quality, 'score')
        assert 0.0 <= voice_quality.score <= 100.0
