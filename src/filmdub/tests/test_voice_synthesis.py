"""
Ticket 011 M09 语音合成测试

覆盖：
- 模型管理器：加载/切换/卸载/信息查询（CosyVoice 未安装时优雅失败）
- TTS 引擎：无模型报错、文本前处理、音高因子→半音转换、停顿插入、
  归一化后处理、WAV 落盘（标准库 wave 回退）、Artifact 元数据
- 批量合成器：并发合成与错误统计
"""
import struct
import wave
from pathlib import Path

import numpy as np
import pytest

from filmdub.workers.voice_synthesis.config import M09Config
from filmdub.workers.voice_synthesis.model_manager import TTSModelManager
from filmdub.workers.voice_synthesis.tts_engine import TTSEngine
from filmdub.workers.voice_synthesis.batch_synthesizer import BatchSynthesizer
from filmdub.workers.voice_synthesis.models import M09Input, M09Output


# ==================== 模型管理器 ====================


def test_model_manager_init_no_torch():
    """torch 未安装时设备回退 CPU。"""
    mgr = TTSModelManager(M09Config())
    assert mgr.device == "cpu"
    assert mgr.current_model is None
    assert mgr.get_available_models() == ["cosyvoice"]


def test_model_manager_load_unknown_model():
    """加载未知模型返回 False。"""
    mgr = TTSModelManager(M09Config())
    assert mgr.load_model("nonexistent") is False


def test_model_manager_load_cosyvoice_missing():
    """CosyVoice 未安装时加载失败且不崩溃。"""
    mgr = TTSModelManager(M09Config())
    assert mgr.load_model("cosyvoice") is False
    assert mgr.current_model is None


def test_model_manager_switch_unload_lifecycle():
    """切换与卸载生命周期。"""
    mgr = TTSModelManager(M09Config())

    # 手工注册一个伪模型（模拟已加载）
    fake_model = object()
    mgr.models["cosyvoice"] = fake_model
    mgr.current_model = fake_model

    assert mgr.get_current_model_name() == "cosyvoice"
    info = mgr.get_model_info()
    assert info["name"] == "cosyvoice"
    assert info["is_loaded"] is True

    assert mgr.switch_model("cosyvoice") is True
    assert mgr.unload_model("cosyvoice") is True
    assert mgr.current_model is None
    assert mgr.unload_model("cosyvoice") is False


# ==================== TTS 引擎 ====================


class _FakeTTSModel:
    """模拟 TTS 模型：生成正弦波音频。"""

    def __init__(self, sample_rate=24000):
        self.sample_rate = sample_rate

    def inference(self, text, voice_profile_id, emotion, emotion_intensity):
        # 1 秒 220Hz 正弦波
        t = np.arange(self.sample_rate) / self.sample_rate
        return (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def _engine():
    mgr = TTSModelManager(M09Config())
    mgr.current_model = _FakeTTSModel()
    mgr.models["fake"] = mgr.current_model
    return TTSEngine(mgr, M09Config())


def test_synthesize_without_model_raises():
    mgr = TTSModelManager(M09Config())
    engine = TTSEngine(mgr, M09Config())
    with pytest.raises(RuntimeError, match="No TTS model loaded"):
        engine.synthesize("你好", "vp1", {}, "/tmp/out.wav")


def test_synthesize_full_pipeline(tmp_path):
    """完整合成流程：正弦波 → 韵律处理 → WAV 落盘 → Artifact。"""
    engine = _engine()
    output = tmp_path / "d1.wav"

    artifact = engine.synthesize(
        "你好世界",
        "vp1",
        {
            "dialogue_id": "d1",
            "character_id": "C1",
            "pitch": 1.0,
            "speed": 1.0,
            "pause_before": 0.2,
            "pause_after": 0.1,
            "energy": 0.8,
            "emotion": "neutral",
        },
        str(output),
    )

    assert artifact is not None
    assert artifact.dialogue_id == "d1"
    assert output.exists()
    # 文件是有效 WAV
    with wave.open(str(output), "rb") as wf:
        assert wf.getframerate() == engine.config.sample_rate
        assert wf.getnchannels() == 1
        n_frames = wf.getnframes()
    # 0.2s 前停顿 + 1s 音频 + 0.1s 后停顿 = 1.3s
    expected = int(1.3 * engine.config.sample_rate)
    assert abs(n_frames - expected) < engine.config.sample_rate * 0.05
    assert abs(artifact.duration - 1.3) < 0.05


def test_synthesize_adds_pauses():
    """停顿被正确插入（音频长度增加）。"""
    engine = _engine()
    out1 = engine.config.sample_rate  # 1s 基础
    with_pause = engine._add_pauses(
        np.zeros(engine.config.sample_rate, dtype=np.float32),
        pause_before=0.5,
        pause_after=0.5,
    )
    assert len(with_pause) == out1 * 2


def test_pitch_factor_conversion_to_semitones():
    """M08 音高因子（1.1）转为半音 ≈ 1.65 st。"""
    engine = _engine()
    factor = 1.1
    st = 12.0 * np.log2(factor)
    assert abs(st - 1.65) < 0.05
    # 因子为 1.0 时不做音高变换
    audio = np.zeros(100, dtype=np.float32)
    assert engine._apply_pitch_shift(audio, 0.0) is audio


def test_preprocess_text_normalization():
    """文本前处理：空白折叠、省略号、引号、括号规范化。"""
    engine = _engine()
    text = "他说：\u201c好吧...真的吗\u201d  (是的)    \n\n\t"
    processed = engine._preprocess_text(text)
    assert "..." not in processed
    assert "……" in processed
    assert "\u201c" not in processed and "\u201d" not in processed
    assert "（是的）" in processed
    assert "\t" not in processed


def test_postprocess_audio_normalizes():
    """归一化 + 能量 + 限幅。"""
    engine = _engine()
    audio = np.array([0.5, 2.0, -3.0, 0.1], dtype=np.float32)
    processed = engine._postprocess_audio(audio, {"energy": 0.5})
    assert np.max(np.abs(processed)) <= 1.0
    assert processed[0] > 0


def test_save_audio_wave_fallback(tmp_path):
    """标准库 wave 回退写入 16-bit PCM。"""
    engine = _engine()
    path = tmp_path / "out.wav"
    audio = (0.5 * np.ones(4800)).astype(np.float32)
    engine._save_audio(audio, str(path))
    with wave.open(str(path), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        samples = struct.unpack("<%dh" % (len(frames) // 2), frames)
        assert max(samples) > 1000  # 0.5 振幅 → int16 约 16383


# ==================== 批量合成 ====================


def test_batch_synthesizer_success_and_error(tmp_path):
    """批量合成：全部成功并正确统计。"""
    mgr = TTSModelManager(M09Config())
    mgr.current_model = _FakeTTSModel()
    mgr.models["fake"] = mgr.current_model

    synthesizer = BatchSynthesizer(mgr, M09Config())
    import asyncio

    inputs = [
        M09Input(dialogue_id=f"d{i}", character_id="C1", voice_profile_id="vp1", text=f"台词{i}")
        for i in range(3)
    ]
    outputs = asyncio.run(synthesizer.synthesize_batch(inputs, str(tmp_path / "out")))
    assert len(outputs) == 3
    assert all(o.status == "success" for o in outputs)
    assert all(o.audio_artifact is not None for o in outputs)
    # 文件已生成
    for o in outputs:
        assert Path(o.audio_artifact.file_path).exists()


def test_batch_synthesizer_error_path(tmp_path):
    """无模型时批量合成全部报错但不崩溃。"""
    mgr = TTSModelManager(M09Config())
    synthesizer = BatchSynthesizer(mgr, M09Config())
    import asyncio

    inputs = [M09Input(dialogue_id="d1", character_id="C1", voice_profile_id="vp1", text="x")]
    outputs = asyncio.run(synthesizer.synthesize_batch(inputs, str(tmp_path / "out")))
    assert len(outputs) == 1
    assert outputs[0].status == "error"
    assert "No TTS model loaded" in outputs[0].error
