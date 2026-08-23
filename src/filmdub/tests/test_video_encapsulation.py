"""
M12 视频封装模块测试
"""
import pytest
import os
import tempfile
from pathlib import Path

from filmdub.workers.video_encapsulation import (
    M12Config,
    VideoEncapsulationWorker,
    EncapsulationInput,
    EncapsulationResult,
    AudioTrack,
    SubtitleTrack,
    VideoQuality,
    SubtitleMode
)


class TestM12Config:
    """M12 配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = M12Config()
        assert config.ffmpeg_path == "ffmpeg"
        assert config.video_codec == "libx264"
        assert config.audio_codec == "aac"
        assert config.video_bitrate == "2M"
        assert config.audio_bitrate == "192k"
        assert config.dialogue_volume == 1.0
        assert config.background_volume == 0.3

    def test_custom_config(self):
        """测试自定义配置"""
        config = M12Config(
            video_codec="libx265",
            audio_codec="libopus",
            video_bitrate="4M",
            dialogue_volume=0.9
        )
        assert config.video_codec == "libx265"
        assert config.audio_codec == "libopus"
        assert config.video_bitrate == "4M"
        assert config.dialogue_volume == 0.9


class TestAudioTrack:
    """音轨模型测试"""

    def test_audio_track_creation(self):
        """测试创建音轨"""
        track = AudioTrack(
            file_path="/path/to/audio.wav",
            volume=0.8,
            language="chi",
            is_default=True
        )
        assert track.file_path == "/path/to/audio.wav"
        assert track.volume == 0.8
        assert track.language == "chi"
        assert track.is_default is True

    def test_audio_track_defaults(self):
        """测试音轨默认值"""
        track = AudioTrack(file_path="/path/to/audio.wav")
        assert track.volume == 1.0
        assert track.language is None
        assert track.is_default is False


class TestSubtitleTrack:
    """字幕模型测试"""

    def test_subtitle_track_creation(self):
        """测试创建字幕"""
        subtitle = SubtitleTrack(
            file_path="/path/to/subtitle.srt",
            language="chi",
            mode=SubtitleMode.HARD,
            font_name="Microsoft YaHei",
            font_size=28
        )
        assert subtitle.file_path == "/path/to/subtitle.srt"
        assert subtitle.language == "chi"
        assert subtitle.mode == SubtitleMode.HARD
        assert subtitle.font_name == "Microsoft YaHei"
        assert subtitle.font_size == 28


class TestVideoQuality:
    """视频质量控制测试"""

    def test_video_quality_creation(self):
        """测试创建质量控制"""
        quality = VideoQuality(
            width=1920,
            height=1080,
            bitrate="4M",
            fps=30,
            crf=20
        )
        assert quality.width == 1920
        assert quality.height == 1080
        assert quality.bitrate == "4M"
        assert quality.fps == 30
        assert quality.crf == 20


class TestEncapsulationInput:
    """封装输入测试"""

    def test_encapsulation_input_creation(self):
        """测试创建封装输入"""
        input_data = EncapsulationInput(
            video_file="/path/to/video.mp4",
            output_file="/path/to/output.mp4"
        )
        assert input_data.video_file == "/path/to/video.mp4"
        assert input_data.output_file == "/path/to/output.mp4"
        assert len(input_data.audio_tracks) == 0
        assert input_data.subtitle_track is None

    def test_encapsulation_input_with_tracks(self):
        """测试带音轨和字幕的封装输入"""
        input_data = EncapsulationInput(
            video_file="/path/to/video.mp4",
            audio_tracks=[
                AudioTrack(file_path="/path/to/dialogue.wav", volume=1.0),
                AudioTrack(file_path="/path/to/background.wav", volume=0.3)
            ],
            subtitle_track=SubtitleTrack(
                file_path="/path/to/subtitle.srt",
                mode=SubtitleMode.SOFT
            ),
            output_file="/path/to/output.mp4"
        )
        assert len(input_data.audio_tracks) == 2
        assert input_data.subtitle_track is not None
        assert input_data.subtitle_track.mode == SubtitleMode.SOFT


class TestVideoEncapsulationWorker:
    """视频封装 Worker 测试"""

    def test_init(self):
        """测试初始化"""
        worker = VideoEncapsulationWorker()
        assert worker.config is not None
        assert worker.config.ffmpeg_path == "ffmpeg"

    def test_init_with_config(self):
        """测试使用自定义配置初始化"""
        config = M12Config(ffmpeg_path="/usr/bin/ffmpeg")
        worker = VideoEncapsulationWorker(config)
        assert worker.config.ffmpeg_path == "/usr/bin/ffmpeg"

    def test_health_check_ffmpeg_available(self, monkeypatch):
        """测试 FFmpeg 可用时的健康检查"""
        def mock_run(*args, **kwargs):
            class MockResult:
                returncode = 0
            return MockResult()

        monkeypatch.setattr("subprocess.run", mock_run)

        worker = VideoEncapsulationWorker()
        assert worker.health_check() is True

    def test_health_check_ffmpeg_unavailable(self, monkeypatch):
        """测试 FFmpeg 不可用时的健康检查"""
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("ffmpeg not found")

        monkeypatch.setattr("subprocess.run", mock_run)

        worker = VideoEncapsulationWorker()
        assert worker.health_check() is False

    def test_process_missing_video_file(self, tmp_path):
        """测试视频文件不存在"""
        worker = VideoEncapsulationWorker()

        input_data = EncapsulationInput(
            video_file="/nonexistent/video.mp4",
            output_file=str(tmp_path / "output.mp4")
        )

        result = worker.process(input_data)
        assert result.success is False
        assert "视频文件不存在" in result.error_message

    def test_process_missing_audio_file(self, tmp_path):
        """测试音频文件不存在"""
        # 创建一个假的视频文件
        video_file = tmp_path / "video.mp4"
        video_file.write_text("fake video")

        worker = VideoEncapsulationWorker()

        input_data = EncapsulationInput(
            video_file=str(video_file),
            audio_tracks=[
                AudioTrack(file_path="/nonexistent/audio.wav")
            ],
            output_file=str(tmp_path / "output.mp4")
        )

        result = worker.process(input_data)
        assert result.success is False
        assert "音频文件不存在" in result.error_message

    def test_validate_inputs_creates_output_dir(self, tmp_path):
        """测试创建输出目录"""
        worker = VideoEncapsulationWorker()

        # 创建一个假的视频文件
        video_file = tmp_path / "video.mp4"
        video_file.write_text("fake video")

        output_file = tmp_path / "subdir" / "output.mp4"
        input_data = EncapsulationInput(
            video_file=str(video_file),
            output_file=str(output_file)
        )

        # 调用 _validate_inputs
        worker._validate_inputs(input_data)

        # 检查目录是否创建
        assert output_file.parent.exists()

    def test_close(self):
        """测试关闭 Worker"""
        worker = VideoEncapsulationWorker()
        worker.close()  # 不应该抛出异常

    def test_ensure_temp_dir(self):
        """测试确保临时目录存在"""
        config = M12Config(temp_dir="/tmp/test_filmdub_temp")
        worker = VideoEncapsulationWorker(config)
        assert os.path.exists(config.temp_dir)
        # 清理
        import shutil
        if os.path.exists(config.temp_dir):
            shutil.rmtree(config.temp_dir)


class TestEncapsulationResult:
    """封装结果测试"""

    def test_encapsulation_result_success(self):
        """测试成功的封装结果"""
        result = EncapsulationResult(
            success=True,
            output_file="/path/to/output.mp4",
            duration=3600.0,
            size_bytes=1024 * 1024 * 1024,  # 1GB
            resolution="1920x1080",
            fps=30.0
        )
        assert result.success is True
        assert result.output_file == "/path/to/output.mp4"
        assert result.duration == 3600.0
        assert result.size_bytes == 1024 * 1024 * 1024
        assert result.resolution == "1920x1080"
        assert result.fps == 30.0

    def test_encapsulation_result_failure(self):
        """测试失败的封装结果"""
        result = EncapsulationResult(
            success=False,
            output_file="/path/to/output.mp4",
            duration=0,
            size_bytes=0,
            resolution="",
            fps=0,
            error_message="FFmpeg 执行失败"
        )
        assert result.success is False
        assert result.error_message == "FFmpeg 执行失败"
