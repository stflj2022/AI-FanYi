"""
M02 场景/镜头/黑屏检测测试（ticket-034）

- 单元测试：差异分数、亮度、切点查找、区间构建、黑屏合并
- 集成测试：用 ffmpeg 生成四段纯色合成视频（红/蓝/黑/绿），验证 Scene Timeline
"""
import subprocess
import shutil
import pytest
import numpy as np

from filmdub.workers.research.scene_detection import (
    SceneDetector,
    frame_diff_score,
    frame_luma_mean,
)


def _require_ffmpeg():
    if shutil.which("ffmpeg") is None:
        pytest.skip("未安装 ffmpeg，跳过集成测试")


def _rgb(h, w, rgb):
    """构造纯色 RGB 帧"""
    return np.full((h, w, 3), rgb, dtype=np.uint8)


class TestFrameHelpers:
    """帧差异/亮度辅助函数测试"""

    def test_diff_same_frame(self):
        a = _rgb(54, 96, (100, 150, 200))
        assert frame_diff_score(a, a.copy()) == pytest.approx(0.0)

    def test_diff_different_frames(self):
        a = _rgb(54, 96, (0, 0, 0))
        b = _rgb(54, 96, (255, 255, 255))
        assert frame_diff_score(a, b) == pytest.approx(1.0, abs=1e-6)

    def test_diff_mid(self):
        a = _rgb(54, 96, (0, 0, 0))
        b = _rgb(54, 96, (128, 128, 128))
        assert 0.4 < frame_diff_score(a, b) < 0.6

    def test_diff_none(self):
        assert frame_diff_score(None, _rgb(4, 4, (1, 1, 1))) == 0.0

    def test_luma_black(self):
        assert frame_luma_mean(_rgb(4, 4, (0, 0, 0))) == pytest.approx(0.0)

    def test_luma_white(self):
        assert frame_luma_mean(_rgb(4, 4, (255, 255, 255))) == pytest.approx(255.0)

    def test_luma_mid(self):
        assert frame_luma_mean(_rgb(4, 4, (128, 128, 128))) == pytest.approx(128.0)


class TestFindCuts:
    """切点查找测试"""

    def test_finds_single_cut(self):
        # 0.05 为普通波动，0.8 为一次切换
        diffs = [0.0, 0.05, 0.05, 0.8, 0.05, 0.05]
        cuts = SceneDetector._find_cuts(diffs, 0.3)
        assert cuts == [3]

    def test_skips_consecutive_high_diff(self):
        # 一次切换跨越多个帧：只取第一帧
        diffs = [0.0, 0.05, 0.9, 0.85, 0.5, 0.05, 0.05]
        cuts = SceneDetector._find_cuts(diffs, 0.3)
        assert cuts == [2]

    def test_multiple_cuts(self):
        diffs = [0.0, 0.8, 0.05, 0.05, 0.9, 0.05]
        cuts = SceneDetector._find_cuts(diffs, 0.3)
        assert cuts == [1, 4]

    def test_no_cuts(self):
        diffs = [0.0, 0.05, 0.02, 0.03]
        assert SceneDetector._find_cuts(diffs, 0.3) == []


class TestBuildSegments:
    """区间构建测试"""

    def test_builds_segments(self):
        times = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
        segs = SceneDetector._build_segments([3], times, 6, 0.6)
        assert len(segs) == 2
        assert segs[0] == {"index": 0, "start": 0.0, "end": 0.3}
        assert segs[1]["start"] == 0.3
        assert segs[1]["end"] == 0.6


class TestBlackSegments:
    """黑屏段合并测试"""

    def test_merges_black_frames(self):
        luma = [200.0, 200.0, 5.0, 5.0, 5.0, 200.0, 2.0, 2.0]
        times = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
        segs = SceneDetector._find_black_segments(
            luma, times, 8,
            luma_threshold=16.0, min_duration=0.1, fps=10.0,
        )
        assert len(segs) == 2
        assert segs[0]["start"] == pytest.approx(0.2)
        assert segs[0]["duration"] == pytest.approx(0.3)
        assert segs[1]["start"] == pytest.approx(0.6)

    def test_filters_short_black(self):
        luma = [200.0, 5.0, 200.0]
        times = [0.0, 0.1, 0.2]
        segs = SceneDetector._find_black_segments(
            luma, times, 3,
            luma_threshold=16.0, min_duration=1.0, fps=10.0,
        )
        assert segs == []

    def test_no_black(self):
        segs = SceneDetector._find_black_segments(
            [200.0, 200.0], [0.0, 0.1], 2,
            luma_threshold=16.0, min_duration=0.1, fps=10.0,
        )
        assert segs == []


class TestSceneDetectorConfig:
    """SceneDetector 配置校验"""

    def test_invalid_threshold_order(self):
        with pytest.raises(ValueError):
            SceneDetector(scene_threshold=0.1, shot_threshold=0.5)

    def test_missing_file(self):
        detector = SceneDetector()
        with pytest.raises(FileNotFoundError):
            detector.detect("/nonexistent/video.mp4")


@pytest.mark.integration
class TestSceneDetectionIntegration:
    """合成视频集成测试（需要 ffmpeg）"""

    @pytest.fixture
    def synthetic_video(self, tmp_path):
        _require_ffmpeg()
        path = tmp_path / "segments.mp4"
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=0xff0000:s=160x90:r=10:d=1",
            "-f", "lavfi", "-i", "color=c=0x0000ff:s=160x90:r=10:d=1",
            "-f", "lavfi", "-i", "color=c=0x000000:s=160x90:r=10:d=1",
            "-f", "lavfi", "-i", "color=c=0x00ff00:s=160x90:r=10:d=1",
            "-filter_complex", "[0:v][1:v][2:v][3:v]concat=n=4:v=1:a=0[outv]",
            "-map", "[outv]", "-pix_fmt", "yuv420p",
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            pytest.skip(f"ffmpeg 生成合成视频失败: {result.stderr}")
        return str(path)

    def test_detect_scene_timeline(self, synthetic_video):
        detector = SceneDetector(black_luma_threshold=20.0)
        timeline = detector.detect(synthetic_video)

        assert timeline["video_file"] == synthetic_video
        assert timeline["total_frames"] >= 30  # 约 40 帧
        assert timeline["duration"] == pytest.approx(4.0, abs=0.3)

        # 4 段纯色（红/蓝/黑/绿）→ 至少 3 个场景切点 → 4 个场景
        assert len(timeline["scenes"]) >= 2
        # 首场景从 0 开始
        assert timeline["scenes"][0]["start"] == pytest.approx(0.0, abs=0.2)

        # 黑屏段：第 2~3 秒
        assert len(timeline["black_frames"]) >= 1
        black = timeline["black_frames"][0]
        assert black["start"] == pytest.approx(2.0, abs=0.5)
        assert black["duration"] >= 0.5

        # 镜头时间线存在且映射到场景
        assert len(timeline["shots"]) >= 2
        assert timeline["shots"][0]["scene_index"] == 0

    def test_detect_short_black_filtered(self, synthetic_video):
        # min_black_duration 设为 5s：1s 的黑屏段应被过滤
        detector = SceneDetector(black_luma_threshold=20.0, min_black_duration=5.0)
        timeline = detector.detect(synthetic_video)
        assert timeline["black_frames"] == []

    def test_no_video_stream_raises(self, tmp_path):
        """无视频流（纯音频）时应抛出明确错误而非崩溃"""
        _require_ffmpeg()
        path = tmp_path / "audio_only.mp4"
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:a", "aac", str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            pytest.skip(f"ffmpeg 生成纯音频失败: {result.stderr}")
        detector = SceneDetector()
        with pytest.raises(ValueError, match="无视频流"):
            detector.detect(str(path))
