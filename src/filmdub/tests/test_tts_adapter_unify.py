"""
TTS Adapter 统一测试（ticket-035）

覆盖：
- VoiceAdapter factory 后端路由（qwen/cosyvoice/f5-tts）
- CosyVoiceAdapter / F5TTSAdapter 实现 VoiceAdapterInterface.synthesize
- 本地适配器 numpy→WAV 落盘
- TTSModelManager.create_adapter / synthesize_via_adapter 统一入口
- TTSEngine.synthesize_async 走 Adapter 且模型版本进入 Artifact
"""
import wave
from pathlib import Path

import numpy as np
import pytest

from filmdub.adapter import (
    VoiceAdapter,
    QwenTTSAdapter,
    CosyVoiceAdapter,
    F5TTSAdapter,
    LocalVoiceAdapter,
)
from filmdub.workers.voice_synthesis.config import M09Config
from filmdub.workers.voice_synthesis.model_manager import TTSModelManager
from filmdub.workers.voice_synthesis.models import AudioArtifact
from filmdub.workers.voice_synthesis.tts_engine import TTSEngine


# ----------------------------------------------------------------------
# 伪模型（模拟 CosyVoice / F5-TTS 的返回结构）
# ----------------------------------------------------------------------
class _FakeCosyVoiceModel:
    version = "test-cosy-1.0"

    def inference_zero_shot(self, tts_text, prompt_text, prompt_speech_16k):
        audio = np.zeros(22050, dtype=np.float32)
        return iter([{"tts_speech": audio, "sample_rate": 22050}])

    def inference_speech(self, tts_text):
        audio = np.zeros(22050, dtype=np.float32)
        return iter([{"tts_speech": audio, "sample_rate": 22050}])


class _FakeF5Model:
    version = "test-f5-2.0"

    def infer(self, ref_file, ref_text, gen_text, speed):
        audio = np.zeros(24000, dtype=np.float32)
        return audio, 24000


def _write_wav(path: Path, sr: int, seconds: float = 1.0):
    path = Path(path).with_suffix(".wav")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((np.zeros(int(sr * seconds)).astype(np.int16)).tobytes())
    return path


# ----------------------------------------------------------------------
# VoiceAdapter factory
# ----------------------------------------------------------------------
class TestVoiceAdapterFactory:
    def test_factory_qwen(self):
        adapter = VoiceAdapter(backend="qwen", base_url="http://localhost:1")
        try:
            assert isinstance(adapter._adapter, QwenTTSAdapter)
        finally:
            import asyncio
            asyncio.run(adapter.close())

    def test_factory_cosyvoice(self):
        adapter = VoiceAdapter(backend="cosyvoice")
        assert isinstance(adapter._adapter, CosyVoiceAdapter)

    def test_factory_f5_tts(self):
        adapter = VoiceAdapter(backend="f5-tts")
        assert isinstance(adapter._adapter, F5TTSAdapter)

    def test_factory_underscore_normalized(self):
        adapter = VoiceAdapter(backend="f5_tts")
        assert isinstance(adapter._adapter, F5TTSAdapter)

    def test_factory_unknown(self):
        with pytest.raises(ValueError):
            VoiceAdapter(backend="nonexistent")

    def test_model_info_delegation(self):
        adapter = VoiceAdapter(backend="cosyvoice")
        info = adapter.model_info()
        assert info["model_name"] == "CosyVoice-300M"


# ----------------------------------------------------------------------
# 本地适配器
# ----------------------------------------------------------------------
class TestLocalVoiceAdapter:
    def test_save_audio_wav(self, tmp_path):
        audio = np.linspace(-1.0, 1.0, 24000).astype(np.float32)
        out = LocalVoiceAdapter._save_audio(audio, 24000, tmp_path / "test.wav")
        assert out.exists()
        with wave.open(str(out), "rb") as wf:
            assert wf.getframerate() == 24000
            assert wf.getnframes() == 24000

    def test_save_audio_adds_wav_suffix(self, tmp_path):
        audio = np.zeros(8000, dtype=np.float32)
        out = LocalVoiceAdapter._save_audio(audio, 8000, tmp_path / "no_ext")
        assert out.suffix == ".wav"
        assert out.exists()

    def test_save_audio_int16(self, tmp_path):
        audio = np.zeros(8000, dtype=np.int16)
        out = LocalVoiceAdapter._save_audio(audio, 8000, tmp_path / "i16.wav")
        assert out.exists()


class TestCosyVoiceAdapter:
    @pytest.mark.asyncio
    async def test_synthesize_with_mock_model(self, tmp_path, monkeypatch):
        adapter = CosyVoiceAdapter()
        monkeypatch.setattr(adapter, "_load_model", lambda: _FakeCosyVoiceModel())
        out = await adapter.synthesize("你好", "default", tmp_path / "speech.wav")
        assert out.exists()
        assert out.suffix == ".wav"

    @pytest.mark.asyncio
    async def test_synthesize_zero_shot_with_reference(self, tmp_path, monkeypatch):
        adapter = CosyVoiceAdapter()
        calls = {}

        def fake_inference_zero_shot(tts_text, prompt_text, prompt_speech_16k):
            calls["prompt_speech"] = prompt_speech_16k
            audio = np.zeros(22050, dtype=np.float32)
            return iter([{"tts_speech": audio, "sample_rate": 22050}])

        fake = _FakeCosyVoiceModel()
        fake.inference_zero_shot = fake_inference_zero_shot
        monkeypatch.setattr(adapter, "_load_model", lambda: fake)
        await adapter.synthesize(
            "你好", "ref_id", tmp_path / "s.wav",
            reference_audio="/tmp/ref.wav", prompt_text="提示",
        )
        assert calls.get("prompt_speech") == "/tmp/ref.wav"

    @pytest.mark.asyncio
    async def test_model_info(self, monkeypatch):
        adapter = CosyVoiceAdapter()
        monkeypatch.setattr(adapter, "_load_model", lambda: _FakeCosyVoiceModel())
        await adapter._get_model()
        info = adapter.model_info()
        assert info["model_name"] == "CosyVoice-300M"
        assert info["model_version"] == "test-cosy-1.0"

    def test_load_missing_library(self):
        adapter = CosyVoiceAdapter()
        # 未安装 cosyvoice 库时应抛出 ImportError
        with pytest.raises(ImportError):
            import asyncio
            asyncio.run(adapter._get_model())


class TestF5TTSAdapter:
    @pytest.mark.asyncio
    async def test_synthesize_with_mock_model(self, tmp_path, monkeypatch):
        adapter = F5TTSAdapter()
        monkeypatch.setattr(adapter, "_load_model", lambda: _FakeF5Model())
        out = await adapter.synthesize("你好", "default", tmp_path / "speech.wav")
        assert out.exists()
        info = adapter.model_info()
        assert info["model_version"] == "test-f5-2.0"


# ----------------------------------------------------------------------
# TTSModelManager 统一入口
# ----------------------------------------------------------------------
class TestModelManagerAdapter:
    def test_create_adapter_cosyvoice(self):
        mgr = TTSModelManager(M09Config())
        adapter = mgr.create_adapter("cosyvoice")
        assert isinstance(adapter._adapter, CosyVoiceAdapter)

    def test_create_adapter_default_from_config(self):
        # default_model = "cosyvoice"
        mgr = TTSModelManager(M09Config())
        adapter = mgr.create_adapter()
        assert isinstance(adapter._adapter, CosyVoiceAdapter)

    def test_create_adapter_f5(self):
        mgr = TTSModelManager(M09Config(enable_f5_tts=True))
        adapter = mgr.create_adapter("f5_tts")
        assert isinstance(adapter._adapter, F5TTSAdapter)

    def test_create_adapter_qwen(self):
        mgr = TTSModelManager(M09Config(default_model="qwen"))
        adapter = mgr.create_adapter("qwen", base_url="http://localhost:1")
        assert isinstance(adapter._adapter, QwenTTSAdapter)

    @pytest.mark.asyncio
    async def test_synthesize_via_adapter(self, tmp_path):
        mgr = TTSModelManager(M09Config())

        class FakeAdapter:
            def __init__(self):
                self.closed = False

            async def synthesize(self, text, voice_id, output_path, speed=1.0, pitch=1.0, **kw):
                _write_wav(Path(output_path), 24000)
                return Path(output_path).with_suffix(".wav")

            def model_info(self):
                return {"model_name": "fake", "model_version": "1.0"}

            async def close(self):
                self.closed = True

        fake = FakeAdapter()
        mgr.create_adapter = lambda *a, **k: fake

        out, info = await mgr.synthesize_via_adapter(
            "你好", "v1", str(tmp_path / "a.wav"), speed=1.2
        )
        assert Path(out).exists()
        assert info["model_name"] == "fake"
        assert fake.closed is True  # 用完关闭


# ----------------------------------------------------------------------
# AudioArtifact 模型信息 / TTSEngine Adapter 合成
# ----------------------------------------------------------------------
class TestAudioArtifactModelInfo:
    def test_artifact_carries_tts_model(self):
        art = AudioArtifact(
            artifact_id="a1",
            dialogue_id="d1",
            character_id="c1",
            file_path="/tmp/x.wav",
            duration=1.0,
            sample_rate=24000,
            tts_model="cosyvoice",
            tts_model_version="1.0",
            tts_config={"backend": "cosyvoice", "device": "cpu"},
        )
        d = art.to_dict()
        assert d["tts_model"] == "cosyvoice"
        assert d["tts_model_version"] == "1.0"
        assert d["tts_config"]["backend"] == "cosyvoice"

    def test_artifact_defaults(self):
        art = AudioArtifact(
            artifact_id="a1", dialogue_id="d1", character_id="c1",
            file_path="/tmp/x.wav", duration=1.0, sample_rate=24000,
        )
        d = art.to_dict()
        assert d["tts_model"] is None
        assert d["tts_model_version"] is None


class TestTTSEngineAdapter:
    @pytest.mark.asyncio
    async def test_synthesize_async(self, tmp_path):
        mgr = TTSModelManager(M09Config())

        async def fake_synth(text, voice_id, output_path, speed=1.0, pitch=1.0, **kw):
            path = _write_wav(Path(output_path), 24000)
            return path, {"model_name": "qwen", "model_version": "9.9"}

        mgr.synthesize_via_adapter = fake_synth
        engine = TTSEngine(mgr, M09Config(sample_rate=24000))

        artifact = await engine.synthesize_async(
            "你好",
            "vp1",
            {"dialogue_id": "d1", "character_id": "C1"},
            str(tmp_path / "out.wav"),
        )
        assert artifact is not None
        assert artifact.tts_model == "qwen"
        assert artifact.tts_model_version == "9.9"
        assert artifact.duration > 0
        assert artifact.file_path.endswith(".wav")

    @pytest.mark.asyncio
    async def test_synthesize_async_failure_returns_none(self, tmp_path):
        mgr = TTSModelManager(M09Config())

        async def fail_synth(*a, **k):
            raise RuntimeError("backend down")

        mgr.synthesize_via_adapter = fail_synth
        engine = TTSEngine(mgr, M09Config(sample_rate=24000))
        artifact = await engine.synthesize_async("你好", "vp1", {}, str(tmp_path / "o.wav"))
        assert artifact is None


# ----------------------------------------------------------------------
# Qwen 后端 model_info / BatchSynthesizer Adapter 统一路径
# ----------------------------------------------------------------------
class TestQwenModelInfo:
    def test_qwen_model_info(self):
        import asyncio

        adapter = QwenTTSAdapter(base_url="http://localhost:8081")
        try:
            info = adapter.model_info()
            assert info["backend"] == "qwen"
            assert info["model_name"] == "qwen-tts"
            assert "base_url" in info
        finally:
            asyncio.run(adapter.close())


class TestBatchSynthesizerAdapter:
    """生产批量路径走 Adapter 统一入口（ticket-035）"""

    @pytest.mark.asyncio
    async def test_batch_synthesizer_uses_adapter(self, tmp_path):
        from filmdub.workers.voice_synthesis.batch_synthesizer import BatchSynthesizer
        from filmdub.workers.voice_synthesis.models import M09Input

        mgr = TTSModelManager(M09Config())

        async def fake_synth(text, voice_id, output_path, speed=1.0, pitch=1.0, **kw):
            path = _write_wav(Path(output_path), 24000)
            return path, {"model_name": "qwen", "model_version": "9.9"}

        mgr.synthesize_via_adapter = fake_synth
        synthesizer = BatchSynthesizer(mgr, M09Config(use_adapter=True))

        inputs = [
            M09Input(dialogue_id="d1", character_id="C1", voice_profile_id="vp1", text="你好"),
            M09Input(dialogue_id="d2", character_id="C1", voice_profile_id="vp1", text="世界"),
        ]
        outputs = await synthesizer.synthesize_batch(inputs, str(tmp_path / "out"))
        assert len(outputs) == 2
        assert all(o.status == "success" for o in outputs)
        # 模型版本进入 Artifact
        assert outputs[0].audio_artifact.tts_model == "qwen"
        assert outputs[0].audio_artifact.tts_model_version == "9.9"
        assert Path(outputs[0].audio_artifact.file_path).exists()

    @pytest.mark.asyncio
    async def test_batch_synthesizer_adapter_failure(self, tmp_path):
        from filmdub.workers.voice_synthesis.batch_synthesizer import BatchSynthesizer
        from filmdub.workers.voice_synthesis.models import M09Input

        mgr = TTSModelManager(M09Config())

        async def fail_synth(*a, **k):
            raise RuntimeError("backend down")

        mgr.synthesize_via_adapter = fail_synth
        synthesizer = BatchSynthesizer(mgr, M09Config(use_adapter=True))
        inputs = [M09Input(dialogue_id="d1", character_id="C1", voice_profile_id="vp1", text="x")]
        outputs = await synthesizer.synthesize_batch(inputs, str(tmp_path / "out"))
        assert outputs[0].status == "error"
        # synthesize_async 失败返回 None，批量器报无音频产出（底层错误已写入日志）
        assert "Synthesis returned no audio" in outputs[0].error
