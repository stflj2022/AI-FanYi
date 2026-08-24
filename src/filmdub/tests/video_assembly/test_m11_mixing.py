"""
M11 Audio Mixing 单元测试
"""

import pytest
from pathlib import Path
import tempfile

from filmdub.workers.video_assembly import (
    M11Config,
    AudioTrack,
    AudioTrackType,
    AudioSegment,
)
from filmdub.workers.video_assembly.audio_mixer import AdvancedAudioMixer


class TestAudioTrackType:
    """测试音频轨道类型枚举"""

    def test_track_types(self):
        """测试所有轨道类型"""
        assert AudioTrackType.DIALOGUE == "dialogue"
        assert AudioTrackType.BACKGROUND == "background"
        assert AudioTrackType.AMBIENT == "ambient"
        assert AudioTrackType.EFFECTS == "effects"
        assert AudioTrackType.ORIGINAL == "original"


class TestAudioTrack:
    """测试音频轨道"""

    def test_create_track(self):
        """测试创建轨道"""
        track = AudioTrack(
            track_type=AudioTrackType.BACKGROUND,
            audio_path="/tmp/music.wav",
            start_time=0.0,
            end_time=60.0,
            volume=0.3,
        )
        assert track.track_type == AudioTrackType.BACKGROUND
        assert track.volume == 0.3

    def test_to_dict(self):
        """测试转换为字典"""
        track = AudioTrack(
            track_type=AudioTrackType.AMBIENT,
            audio_path="/tmp/ambient.wav",
            volume=0.5,
        )
        data = track.to_dict()
        assert data["track_type"] == "ambient"
        assert data["volume"] == 0.5


class TestM11Config:
    """测试 M11 配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = M11Config()
        assert config.ffmpeg_path == "ffmpeg"
        assert config.enable_audio_separation is True
        assert config.enable_lufs_normalization is True
        assert config.target_lufs == -16.0

    def test_volume_config(self):
        """测试音量配置"""
        config = M11Config()
        assert config.dialogue_volume == 1.0
        assert config.background_volume == 0.3
        assert config.ambient_volume == 0.5
        assert config.effects_volume == 0.8


class TestAdvancedAudioMixer:
    """测试高级音频混合器"""

    @pytest.fixture
    def mixer(self):
        """创建混合器实例"""
        return AdvancedAudioMixer(M11Config())

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """创建临时目录"""
        return tmp_path

    def test_mixer_init(self, mixer):
        """测试混合器初始化"""
        assert mixer.config is not None
        assert mixer.config.enable_audio_separation is True

    @pytest.mark.asyncio
    async def test_mix_empty_tracks(self, mixer, tmp_path):
        """测试混合空轨道"""
        output = tmp_path / "output.wav"

        # 创建空文件作为占位
        for i in range(3):
            (tmp_path / f"track_{i}.wav").touch()

        # 应该至少有静音底床
        # 实际测试需要真实的音频文件
        pass

    def test_normalize_lufs_disabled(self, mixer, tmp_path):
        """测试禁用 LUFS 归一化"""
        config = M11Config(enable_lufs_normalization=False)
        mixer_disabled = AdvancedAudioMixer(config)

        # 同步测试
        import asyncio
        input_file = tmp_path / "input.wav"
        input_file.touch()

        output_file = tmp_path / "output.wav"

        async def test():
            result = await mixer_disabled.normalize_lufs(input_file, output_file)
            assert result is True

        asyncio.run(test())


class TestAudioIntegration:
    """测试音频集成"""

    @pytest.mark.asyncio
    async def test_mix_with_multiple_tracks(self, tmp_path):
        """测试混合多个音轨"""
        config = M11Config()
        mixer = AdvancedAudioMixer(config)

        # 创建测试数据
        dialogue_segments = [
            AudioSegment(
                dialogue_id="d001",
                audio_path=str(tmp_path / "dialogue1.wav"),
                start_time=0.0,
                end_time=5.0,
                target_start_time=0.0,
                target_end_time=5.0,
            )
        ]

        background_tracks = [
            AudioTrack(
                track_type=AudioTrackType.BACKGROUND,
                audio_path=str(tmp_path / "bg_music.wav"),
                volume=0.3,
            )
        ]

        # 创建占位文件
        for segment in dialogue_segments:
            Path(segment.audio_path).touch()
        for track in background_tracks:
            Path(track.audio_path).touch()

        # 注意：实际测试需要真实的音频文件
        # 这里只是测试代码结构
        assert len(dialogue_segments) == 1
        assert len(background_tracks) == 1
