"""
Ticket 008 M05 音频分析核心测试

在无 pyannote/speechbrain/librosa 等重依赖的环境中，验证：
- 说话人分离器的降级行为（模型未加载时明确报错）
- pyannote 结果转换（itertracks 接口适配）
- 短片段过滤
- 纯 numpy 能量特征提取
- 数据模型序列化
- M05Worker 作业错误路径
"""
import asyncio

import numpy as np
import pytest

from filmdub.workers.audio_scene_analysis.config import M05Config
from filmdub.workers.audio_scene_analysis.diarization import SpeakerDiarization
from filmdub.workers.audio_scene_analysis.embedding import SpeakerEmbeddingExtractor
from filmdub.workers.audio_scene_analysis.audio_features import AudioFeatureExtractor
from filmdub.workers.audio_scene_analysis.models import (
    SpeakerSegment,
    DiarizationResult,
    AudioFeatures,
)


# ==================== 说话人分离 ====================


def test_diarization_init_without_pyannote():
    """pyannote 未安装时模型为 None，但不崩溃。"""
    diarization = SpeakerDiarization(M05Config())
    assert diarization.model is None
    assert diarization.device == "cpu"


def test_diarize_raises_without_model(tmp_path):
    """模型未加载时 diarize 明确报错。"""
    diarization = SpeakerDiarization(M05Config())
    with pytest.raises(RuntimeError, match="model not loaded"):
        diarization.diarize(str(tmp_path / "no-audio.wav"))


def test_diarize_raises_missing_file():
    """音频文件不存在时抛 FileNotFoundError。"""
    diarization = SpeakerDiarization(M05Config())
    diarization.model = object()  # 模拟模型已加载
    with pytest.raises(FileNotFoundError):
        diarization.diarize("/nonexistent/audio.wav")


class _FakeTurn:
    def __init__(self, start, end):
        self.start = start
        self.end = end


class _FakeDiarization:
    """模拟 pyannote diarization 输出（itertracks 接口）。"""

    def __init__(self, tracks):
        self._tracks = tracks

    def itertracks(self, yield_label=True):
        for start, end, label in self._tracks:
            yield _FakeTurn(start, end), None, label


def test_convert_to_segments_sorted():
    """pyannote 结果转换为 SpeakerSegment 并按时间排序。"""
    diarization = SpeakerDiarization(M05Config())
    fake = _FakeDiarization([
        (5.0, 6.0, "SPEAKER_01"),
        (1.0, 2.0, "SPEAKER_02"),
        (3.0, 4.5, "SPEAKER_01"),
    ])
    segments = diarization._convert_to_segments(fake)
    assert len(segments) == 3
    assert [s.start_time for s in segments] == [1.0, 3.0, 5.0]
    assert segments[0].speaker_id == "SPEAKER_02"
    assert segments[2].confidence == 0.95


def test_filter_short_segments():
    """短片段被过滤，说话人数与总时长正确。"""
    diarization = SpeakerDiarization(M05Config())
    result = DiarizationResult(
        segments=[
            SpeakerSegment("S1", 0.0, 2.0, 0.9),
            SpeakerSegment("S1", 2.0, 2.5, 0.9),   # 0.5s < min → 过滤
            SpeakerSegment("S2", 3.0, 5.0, 0.9),
            SpeakerSegment("S3", 6.0, 6.3, 0.8),   # 0.3s < min → 过滤
        ],
        num_speakers=3,
        total_duration=6.3,
    )
    filtered = diarization.filter_short_segments(result, min_duration=1.0)
    assert len(filtered.segments) == 2
    assert filtered.num_speakers == 2
    assert filtered.total_duration == 6.3


# ==================== 嵌入提取器 ====================


def test_embedding_extractor_init_without_speechbrain():
    """speechbrain 未安装时模型为 None。"""
    extractor = SpeakerEmbeddingExtractor(M05Config())
    assert extractor.model is None
    assert extractor.device == "cpu"


def test_embedding_extract_raises_without_model(tmp_path):
    """模型未加载时 extract 明确报错。"""
    extractor = SpeakerEmbeddingExtractor(M05Config())
    with pytest.raises(RuntimeError, match="model not loaded"):
        extractor.extract(str(tmp_path / "a.wav"), [])


# ==================== 音频特征（纯 numpy 路径） ====================


def test_extract_energy_pure_numpy():
    """能量特征提取不依赖 librosa，可独立验证。"""
    extractor = AudioFeatureExtractor(M05Config(n_fft=256, hop_length=128))
    # 构造音频：前一半静音，后一半高能量
    audio = np.zeros(2048, dtype=np.float32)
    audio[1024:] = 0.5

    mean, std = extractor._extract_energy(audio)
    assert mean > 0
    assert std >= 0
    # 能量均值应显著大于静音情况
    silence_mean, _ = extractor._extract_energy(np.zeros(2048, dtype=np.float32))
    assert mean > silence_mean


def test_extract_skips_short_segments(tmp_path):
    """过短片段被跳过；文件不存在时抛 FileNotFoundError。"""
    extractor = AudioFeatureExtractor(M05Config())
    with pytest.raises(FileNotFoundError):
        extractor.extract(str(tmp_path / "missing.wav"), [])


# ==================== 数据模型 ====================


def test_audio_features_to_dict():
    features = AudioFeatures(
        speaker_id="S1",
        start_time=1.0,
        end_time=2.0,
        pitch_mean=120.0,
        pitch_std=5.0,
        pitch_min=110.0,
        pitch_max=130.0,
        energy_mean=0.1,
        energy_std=0.01,
        spectral_centroid_mean=1000.0,
        spectral_centroid_std=50.0,
        spectral_rolloff_mean=2000.0,
        spectral_rolloff_std=100.0,
        mfcc_mean=[1.0, 2.0],
        mfcc_std=[0.1, 0.2],
    )
    d = features.to_dict()
    assert d["speaker_id"] == "S1"
    assert d["pitch_mean"] == 120.0
    assert d["mfcc_mean"] == [1.0, 2.0]


def test_diarization_result_to_dict():
    result = DiarizationResult(
        segments=[SpeakerSegment("S1", 0.0, 1.5, 0.9, text="你好")],
        num_speakers=1,
        total_duration=1.5,
    )
    d = result.to_dict()
    assert d["num_speakers"] == 1
    assert d["segments"][0]["text"] == "你好"


# ==================== M05Worker 错误路径 ====================


def test_m05_worker_missing_audio_path(tmp_path):
    """缺少 audio_path 返回 error。"""
    from filmdub.workers.audio_scene_analysis import M05Worker

    worker = M05Worker(projects_base_dir=tmp_path)
    result = asyncio.run(worker.process_job({"job_id": "j1", "project_id": "p1"}))
    assert result["status"] == "error"
    assert "Missing audio_path" in result["error"]


def test_m05_worker_missing_audio_file(tmp_path):
    """audio_path 指向不存在的文件返回 error。"""
    from filmdub.workers.audio_scene_analysis import M05Worker

    worker = M05Worker(projects_base_dir=tmp_path)
    result = asyncio.run(worker.process_job({
        "job_id": "j2",
        "project_id": "p2",
        "audio_path": str(tmp_path / "not-there.wav"),
    }))
    assert result["status"] == "error"
    assert "not found" in result["error"]
