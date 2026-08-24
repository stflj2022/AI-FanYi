"""
M10 Prosody & Performance 单元测试
"""

import pytest
from pathlib import Path
import tempfile

from filmdub.workers.prosody_performance import (
    M10Worker,
    M10Config,
    ProsodyProcessor,
)
from filmdub.workers.prosody_performance.models import (
    EmotionType,
    ProsodyParams,
    DialogueSegment,
)


class TestM10Config:
    """测试 M10 配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = M10Config()
        assert config.sample_rate == 22050
        assert config.pitch_min == 0.5
        assert config.pitch_max == 2.0
        assert config.speed_min == 0.5
        assert config.speed_max == 2.0

    def test_emotion_params(self):
        """测试情绪参数映射"""
        config = M10Config()

        # 测试中性情绪
        params = config.get_emotion_params("neutral")
        assert params["pitch"] == 1.0
        assert params["speed"] == 1.0
        assert params["volume"] == 1.0

        # 测试快乐情绪
        params = config.get_emotion_params("happy")
        assert params["pitch"] > 1.0
        assert params["speed"] > 1.0
        assert params["volume"] > 1.0

        # 测试悲伤情绪
        params = config.get_emotion_params("sad")
        assert params["pitch"] < 1.0
        assert params["speed"] < 1.0
        assert params["volume"] < 1.0

    def test_clamp_functions(self):
        """测试限制函数"""
        config = M10Config()

        # 测试音高限制
        assert config.clamp_pitch(0.1) == config.pitch_min
        assert config.clamp_pitch(3.0) == config.pitch_max
        assert config.clamp_pitch(1.0) == 1.0

        # 测试语速限制
        assert config.clamp_speed(0.1) == config.speed_min
        assert config.clamp_speed(3.0) == config.speed_max
        assert config.clamp_speed(1.0) == 1.0

        # 测试音量限制
        assert config.clamp_volume(0.1) == config.volume_min
        assert config.clamp_volume(3.0) == config.volume_max
        assert config.clamp_volume(1.0) == 1.0


class TestProsodyParams:
    """测试韵律参数"""

    def test_default_params(self):
        """测试默认参数"""
        params = ProsodyParams()
        assert params.pitch == 1.0
        assert params.speed == 1.0
        assert params.volume == 1.0
        assert params.pause_before == 0.0
        assert params.pause_after == 0.0

    def test_to_dict(self):
        """测试转换为字典"""
        params = ProsodyParams(pitch=1.2, speed=0.9, volume=1.1)
        data = params.to_dict()
        assert data["pitch"] == 1.2
        assert data["speed"] == 0.9
        assert data["volume"] == 1.1

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "pitch": 1.2,
            "speed": 0.9,
            "volume": 1.1,
            "pause_before": 0.1,
            "pause_after": 0.2,
        }
        params = ProsodyParams.from_dict(data)
        assert params.pitch == 1.2
        assert params.speed == 0.9
        assert params.volume == 1.1
        assert params.pause_before == 0.1
        assert params.pause_after == 0.2


class TestDialogueSegment:
    """测试对白片段"""

    def test_create_segment(self):
        """测试创建片段"""
        segment = DialogueSegment(
            dialogue_id="d001",
            text="Hello world",
            audio_path=Path("/tmp/test.wav"),
            speaker="spk1",
            character="Walter",
            emotion=EmotionType.ANGRY,
        )
        assert segment.dialogue_id == "d001"
        assert segment.text == "Hello world"
        assert segment.emotion == EmotionType.ANGRY

    def test_to_dict(self):
        """测试转换为字典"""
        segment = DialogueSegment(
            dialogue_id="d001",
            text="Hello",
            audio_path=Path("/tmp/test.wav"),
            speaker="spk1",
            character="Walter",
        )
        data = segment.to_dict()
        assert data["dialogue_id"] == "d001"
        assert data["text"] == "Hello"
        assert data["emotion"] == "neutral"

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "dialogue_id": "d001",
            "text": "Hello",
            "audio_path": "/tmp/test.wav",
            "speaker": "spk1",
            "character": "Walter",
            "emotion": "happy",
        }
        segment = DialogueSegment.from_dict(data)
        assert segment.dialogue_id == "d001"
        assert segment.emotion == EmotionType.HAPPY


class TestProsodyProcessor:
    """测试韵律处理器"""

    @pytest.fixture
    def processor(self):
        """创建处理器实例"""
        return ProsodyProcessor(M10Config())

    @pytest.fixture
    def sample_audio(self, tmp_path):
        """创建测试音频文件（模拟）"""
        # 注意：实际测试需要真实的音频文件
        # 这里只创建空文件作为占位
        audio_path = tmp_path / "test.wav"
        audio_path.touch()
        return audio_path

    def test_map_emotion_to_prosody(self, processor):
        """测试情绪映射到韵律参数"""
        # 中性情绪
        params = processor.map_emotion_to_prosody(EmotionType.NEUTRAL)
        assert 0.95 <= params.pitch <= 1.05
        assert 0.95 <= params.speed <= 1.05

        # 快乐情绪
        params = processor.map_emotion_to_prosody(EmotionType.HAPPY)
        assert params.pitch > 1.0
        assert params.speed > 1.0
        assert params.volume > 1.0

        # 悲伤情绪
        params = processor.map_emotion_to_prosody(EmotionType.SAD)
        assert params.pitch < 1.0
        assert params.speed < 1.0
        assert params.volume < 1.0

    @pytest.mark.asyncio
    async def test_align_duration(self, processor):
        """测试时长对齐"""
        # 不需要对齐
        speed = await processor.align_duration(
            audio_path=Path("test.wav"),
            target_duration=None,
            current_duration=5.0
        )
        assert speed == 1.0

        # 需要加速
        speed = await processor.align_duration(
            audio_path=Path("test.wav"),
            target_duration=4.0,
            current_duration=5.0
        )
        assert speed > 1.0

        # 需要减速
        speed = await processor.align_duration(
            audio_path=Path("test.wav"),
            target_duration=6.0,
            current_duration=5.0
        )
        assert speed < 1.0


class TestM10Worker:
    """测试 M10 Worker"""

    @pytest.fixture
    def worker(self, tmp_path):
        """创建 Worker 实例"""
        return M10Worker(projects_base_dir=tmp_path)

    @pytest.mark.asyncio
    async def test_health_check(self, worker):
        """测试健康检查"""
        is_healthy = await worker.health_check()
        # 如果系统有 FFmpeg，应该返回 True
        assert isinstance(is_healthy, bool)

    @pytest.mark.asyncio
    async def test_process_empty_job(self, worker):
        """测试处理空作业"""
        result = await worker.process_job({
            "job_id": "test_job",
            "project_id": "test_project",
            "dialogues": [],
        })
        assert result["status"] == "error"
        assert "No dialogues" in result["error"]

    def test_worker_init(self, tmp_path):
        """测试 Worker 初始化"""
        worker = M10Worker(projects_base_dir=tmp_path)
        assert worker.config is not None
        assert worker.processor is not None
        assert worker.projects_base_dir == tmp_path
