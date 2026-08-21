"""
Ticket 012 M11 视频组装测试

使用真实 FFmpeg 生成测试素材并验证：
- 视频信息探测
- 音频轨道替换（结果包含新音频流）
- 字幕嵌入（ASS）后视频仍有效
- 端到端 assemble_video（含 project_id 传递、临时文件清理）
- M11Worker 作业错误路径
"""
import asyncio
import json
import subprocess
from pathlib import Path

import pytest

from filmdub.workers.video_assembly.assembler import VideoAssembler
from filmdub.workers.video_assembly.config import M11Config
from filmdub.workers.video_assembly.models import AudioSegment, SubtitleEntry
from filmdub.workers.video_assembly import M11Worker

pytestmark = pytest.mark.skipif(
    subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode != 0,
    reason="ffmpeg not available",
)


@pytest.fixture
def assembler():
    return VideoAssembler(M11Config())


def _make_video(path: Path, duration: float = 2.0, with_audio: bool = True) -> Path:
    """用 FFmpeg 生成测试视频。"""
    audio_args = ["-f", "lavfi", "-i", "sine=frequency=440:duration=%f" % duration] if with_audio else []
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=blue:size=320x240:duration=%f" % duration,
    ] + audio_args + [
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
    ]
    if with_audio:
        cmd += ["-c:a", "aac", "-shortest"]
    cmd.append(str(path))
    subprocess.run(cmd, check=True, capture_output=True)
    return path


def _make_audio(path: Path, duration: float = 1.0, freq: int = 660) -> Path:
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration}",
        "-c:a", "pcm_s16le",
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


# ==================== 视频信息 ====================


def test_get_video_info(tmp_path):
    """探测视频时长/分辨率/编码。"""
    video = _make_video(tmp_path / "src.mp4", duration=2.0)
    info = asyncio.run(VideoAssembler(M11Config())._get_video_info(str(video)))
    assert abs(info["duration"] - 2.0) < 0.3
    assert info["width"] == 320
    assert info["height"] == 240
    assert info["video_codec"] == "h264"
    assert info["audio_codec"] == "aac"


# ==================== 音频替换 ====================


def test_replace_audio(tmp_path):
    """替换音频后视频有效且音频编码为配置编码。"""
    video = _make_video(tmp_path / "src.mp4", duration=2.0)
    new_audio = _make_audio(tmp_path / "new.wav", duration=1.5)
    output = tmp_path / "replaced.mp4"

    path = asyncio.run(
        VideoAssembler(M11Config())._replace_audio(
            str(video), str(new_audio), str(output), None
        )
    )
    assert path == str(output)
    assert output.exists()

    info = asyncio.run(VideoAssembler(M11Config())._get_video_info(str(output)))
    assert info["audio_codec"] == "aac"
    assert abs(info["duration"] - 1.5) < 0.3  # 以新音频为准（-shortest）


# ==================== 字幕嵌入 ====================


def test_embed_subtitles(tmp_path):
    """ASS 字幕嵌入后视频仍有效。"""
    video = _make_video(tmp_path / "src.mp4", duration=2.0)
    subtitles = [
        SubtitleEntry(index=1, start_time=0.0, end_time=1.0, text="你好，世界"),
        SubtitleEntry(index=2, start_time=1.0, end_time=2.0, text="Hello World"),
    ]
    output = tmp_path / "subbed.mp4"

    subtitle_path = asyncio.run(
        VideoAssembler(M11Config())._embed_subtitles(
            str(video), subtitles, str(output), None
        )
    )
    assert output.exists()
    assert subtitle_path == str(output)

    info = asyncio.run(VideoAssembler(M11Config())._get_video_info(str(output)))
    assert info["video_codec"] == "h264"
    assert info["width"] == 320


# ==================== 端到端组装 ====================


def test_assemble_video_end_to_end(tmp_path):
    """组装：替换音频 + 嵌入字幕 + project_id 传递 + 临时文件清理。"""
    video = _make_video(tmp_path / "src.mp4", duration=2.0)
    seg_audio = _make_audio(tmp_path / "seg1.wav", duration=1.0, freq=880)
    segments = [
        AudioSegment(
            dialogue_id="d1",
            audio_path=str(seg_audio),
            start_time=0.0,
            end_time=1.0,
            target_start_time=0.3,
            target_end_time=1.3,
        )
    ]
    subtitles = [SubtitleEntry(index=1, start_time=0.3, end_time=1.3, text="测试字幕")]
    output = tmp_path / "final.mp4"

    assembler = VideoAssembler(M11Config())
    result = asyncio.run(assembler.assemble_video(
        source_video_path=str(video),
        audio_segments=segments,
        output_path=str(output),
        subtitles=subtitles,
        project_id="proj-m11",
    ))

    assert result.project_id == "proj-m11"
    assert result.video_path == str(output)
    assert output.exists()
    assert result.file_size > 0
    assert "320x240" in result.resolution
    assert result.duration > 0

    # 临时文件已清理（源视频+片段音频之外无残留）
    leftovers = [p for p in tmp_path.iterdir() if p.suffix in (".wav", ".mp4")]
    assert len(leftovers) <= 4  # src.mp4, seg1.wav, final.mp4 (+可能 combined)


def test_assemble_video_without_subtitles(tmp_path):
    """无字幕时直接输出。"""
    video = _make_video(tmp_path / "src.mp4", duration=2.0)
    seg_audio = _make_audio(tmp_path / "seg1.wav", duration=0.8)
    segments = [
        AudioSegment(
            dialogue_id="d1",
            audio_path=str(seg_audio),
            start_time=0.0,
            end_time=0.8,
            target_start_time=0.0,
            target_end_time=0.8,
        )
    ]
    output = tmp_path / "final2.mp4"

    result = asyncio.run(VideoAssembler(M11Config()).assemble_video(
        source_video_path=str(video),
        audio_segments=segments,
        output_path=str(output),
        project_id="p2",
    ))
    assert output.exists()
    assert result.project_id == "p2"
    assert result.subtitle_path is None


def test_assemble_missing_source_raises(tmp_path):
    """源视频不存在时 ffprobe 报错。"""
    assembler = VideoAssembler(M11Config())
    with pytest.raises(RuntimeError):
        asyncio.run(assembler._get_video_info(str(tmp_path / "nope.mp4")))


# ==================== 字幕模型 ====================


def test_subtitle_srt_and_ass_format():
    sub = SubtitleEntry(index=1, start_time=65.5, end_time=66.25, text="你好")
    srt = sub.to_srt()
    assert "00:01:05,500 --> 00:01:06,250" in srt
    assert "你好" in srt

    ass = sub.to_ass()
    assert "Dialogue: 0,0:01:05.50,0:01:06.25,Default" in ass


# ==================== M11Worker ====================


def test_m11_worker_missing_inputs(tmp_path):
    """缺输入参数返回 error。"""
    worker = M11Worker(projects_base_dir=tmp_path)
    result = asyncio.run(worker.process_job({"job_id": "j1", "project_id": "p1"}))
    assert result["status"] == "error"
    assert "Missing source_video_path" in result["error"]


def test_m11_worker_missing_video_file(tmp_path):
    """源视频不存在返回 error。"""
    worker = M11Worker(projects_base_dir=tmp_path)
    result = asyncio.run(worker.process_job({
        "job_id": "j2",
        "project_id": "p2",
        "source_video_path": str(tmp_path / "no.mp4"),
        "output_path": str(tmp_path / "out.mp4"),
    }))
    assert result["status"] == "error"
    assert "not found" in result["error"]


def test_m11_worker_end_to_end(tmp_path):
    """Worker 端到端：真实组装并保存结果 Artifact。"""
    video = _make_video(tmp_path / "src.mp4", duration=1.5)
    seg_audio = _make_audio(tmp_path / "seg.wav", duration=0.7)
    worker = M11Worker(projects_base_dir=tmp_path)

    result = asyncio.run(worker.process_job({
        "job_id": "job-m11-1",
        "project_id": "proj-e2e",
        "source_video_path": str(video),
        "output_path": str(tmp_path / "out.mp4"),
        "audio_segments": [{
            "dialogue_id": "d1",
            "audio_path": str(seg_audio),
            "start_time": 0.0,
            "end_time": 0.7,
            "target_start_time": 0.0,
            "target_end_time": 0.7,
        }],
    }))
    assert result["status"] == "success"
    assert result["result"]["project_id"] == "proj-e2e"
    assert (tmp_path / "out.mp4").exists()
    # 结果 Artifact 已持久化
    artifact = tmp_path / "proj-e2e" / "artifacts" / "final_video.json"
    assert artifact.exists()
    saved = json.loads(artifact.read_text(encoding="utf-8"))
    assert saved["status"] == "success"
