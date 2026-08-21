"""
Ticket 009 M06 说话人映射测试

覆盖说话人→人物映射（嵌入/时长/角色/特征相似度加权）、跨集一致性
（已有映射验证与复用）、未映射处理、音色分配（创建/复用/变体）与
真实音频特征分析（scipy WAV 基频/能量提取）。
"""
import asyncio
import struct
import wave

import numpy as np
import pytest

from filmdub.workers.speaker_mapping.mapper import SpeakerToCharacterMapper
from filmdub.workers.speaker_mapping.voice_assigner import VoiceProfileAssigner
from filmdub.workers.speaker_mapping.models import (
    SpeakerToCharacterMapping,
    VoiceProfile,
)
from filmdub.workers.speaker_mapping.config import M06Config


def _speaker(speaker_id, embedding=None, role_type=None, total_duration=10.0):
    data = {"speaker_id": speaker_id, "total_duration": total_duration}
    if embedding is not None:
        data["embedding"] = embedding
    if role_type:
        data["role_type"] = role_type
    return data


def _character(character_id, name, embedding=None, role_type=None, total_duration=10.0):
    data = {
        "character_id": character_id,
        "name": name,
        "total_duration": total_duration,
        "gender": "male",
        "age_range": "adult",
    }
    if embedding is not None:
        data["reference_embedding"] = embedding
    if role_type:
        data["role_type"] = role_type
    return data


# ==================== 说话人→人物映射 ====================


def test_map_speakers_best_match_by_embedding():
    """嵌入最相似的人物被选中。"""
    mapper = SpeakerToCharacterMapper(M06Config(similarity_threshold=0.7))
    speaker = _speaker("S1", embedding=[1.0, 0.0, 0.0])
    characters = [
        _character("C1", "角色一", embedding=[0.95, 0.1, 0.0]),
        _character("C2", "角色二", embedding=[0.0, 1.0, 0.0]),
    ]
    result = asyncio.run(mapper.map_speakers([speaker], characters))
    assert len(result.mappings) == 1
    assert result.mappings[0].character_id == "C1"
    assert result.mappings[0].similarity > 0.7
    assert result.unmapped_speakers == []


def test_map_speakers_below_threshold_unmapped():
    """低于阈值的说话人不映射。"""
    mapper = SpeakerToCharacterMapper(M06Config(similarity_threshold=0.9))
    speaker = _speaker("S1", embedding=[1.0, 0.0, 0.0])
    characters = [_character("C1", "角色一", embedding=[0.0, 1.0, 0.0])]
    result = asyncio.run(mapper.map_speakers([speaker], characters))
    assert result.mappings == []
    assert result.unmapped_speakers == ["S1"]
    assert result.unmapped_characters == ["C1"]


def test_map_speakers_uses_existing_mappings():
    """跨集一致性：已有映射直接复用，不重新匹配。"""
    mapper = SpeakerToCharacterMapper(M06Config(similarity_threshold=0.5))
    speaker = _speaker("S1", embedding=[1.0, 0.0, 0.0])
    characters = [
        _character("C1", "角色一", embedding=[0.9, 0.0, 0.0]),
        _character("C2", "角色二", embedding=[0.9, 0.1, 0.0]),
    ]
    existing = [
        {"speaker_id": "S1", "character_id": "C2", "confidence": 0.95},
    ]
    result = asyncio.run(
        mapper.map_speakers([speaker], characters, existing_mappings=existing)
    )
    assert len(result.mappings) == 1
    assert result.mappings[0].character_id == "C2"
    assert "继承" in result.mappings[0].notes


def test_map_speakers_existing_mapping_below_threshold_dropped():
    """已有映射相似度低于阈值时被丢弃，走重新匹配。"""
    mapper = SpeakerToCharacterMapper(M06Config(similarity_threshold=0.9))
    speaker = _speaker("S1", embedding=[1.0, 0.0, 0.0])
    characters = [
        _character("C1", "角色一", embedding=[0.0, 1.0, 0.0]),  # 与 S1 完全不同
    ]
    existing = [
        {"speaker_id": "S1", "character_id": "C1", "confidence": 0.9},
    ]
    result = asyncio.run(
        mapper.map_speakers([speaker], characters, existing_mappings=existing)
    )
    # S1 与 C1 相似度过低 → 已有映射被丢弃，且重新匹配也低于阈值
    assert result.mappings == []
    assert result.unmapped_speakers == ["S1"]


def test_calculate_similarity_combines_signals():
    """嵌入+角色类型+时长综合计算相似度。"""
    mapper = SpeakerToCharacterMapper(M06Config())
    speaker = _speaker("S1", embedding=[1.0, 0.0, 0.0], role_type="protagonist")
    character = _character("C1", "角色一", embedding=[1.0, 0.0, 0.0], role_type="protagonist")
    similarity, confidence = asyncio.run(mapper._calculate_similarity(speaker, character))
    assert similarity > 0.9
    assert confidence > 0.5


def test_handle_new_speakers_suggests():
    """未映射说话人生成新人物建议。"""
    mapper = SpeakerToCharacterMapper(M06Config())
    suggestions = mapper._handle_new_speakers(["S9"], [])
    assert len(suggestions) == 1
    assert suggestions[0]["source_speaker_id"] == "S9"
    assert suggestions[0]["requires_review"] is True


# ==================== 音色分配 ====================


def test_assign_voice_profiles_creates():
    """为映射创建参考音色。"""
    assigner = VoiceProfileAssigner(M06Config())
    mapping = SpeakerToCharacterMapping(
        speaker_id="S1",
        character_id="C1",
        similarity=0.9,
        confidence=0.9,
    )
    characters = [_character("C1", "角色一", role_type="protagonist")]
    profiles = asyncio.run(
        assigner.assign_voice_profiles([mapping], characters)
    )
    assert len(profiles) == 1
    vp = profiles[0]
    assert vp.character_id == "C1"
    assert vp.is_reference is True
    assert mapping.voice_profile_id == vp.voice_profile_id
    # 主角风格
    assert vp.style == "confident"


def test_assign_voice_profiles_reuse_existing():
    """已有音色被复用（不重复创建）。"""
    assigner = VoiceProfileAssigner(M06Config(reuse_voice_profiles=True))
    mapping = SpeakerToCharacterMapping(
        speaker_id="S1",
        character_id="C1",
        similarity=0.9,
        confidence=0.9,
    )
    characters = [_character("C1", "角色一")]
    existing = [
        VoiceProfile(
            voice_profile_id="vp_existing",
            character_id="C1",
            name="角色一_vp_existing",
            gender="male",
            age_range="adult",
            style="neutral",
            emotion="neutral",
            pitch=1.0,
            speed=1.0,
            volume=1.0,
            is_reference=True,
        )
    ]
    profiles = asyncio.run(
        assigner.assign_voice_profiles([mapping], characters, existing_voice_profiles=existing)
    )
    assert len(profiles) == 1
    assert profiles[0].voice_profile_id == "vp_existing"
    assert mapping.voice_profile_id == "vp_existing"


def test_assign_voice_profiles_variants():
    """一个说话人多个映射时，多余映射生成确定性变体。"""
    assigner = VoiceProfileAssigner(M06Config(reuse_voice_profiles=True))
    m1 = SpeakerToCharacterMapping(speaker_id="S1", character_id="C1", similarity=0.9, confidence=0.9)
    m2 = SpeakerToCharacterMapping(speaker_id="S2", character_id="C1", similarity=0.9, confidence=0.9)
    characters = [_character("C1", "角色一")]
    existing = [
        VoiceProfile(
            voice_profile_id="vp_ref",
            character_id="C1",
            name="角色一_vp_ref",
            gender="male",
            age_range="adult",
            style="neutral",
            emotion="neutral",
            pitch=1.0,
            speed=1.0,
            volume=1.0,
            is_reference=True,
        )
    ]
    profiles = asyncio.run(
        assigner.assign_voice_profiles([m1, m2], characters, existing_voice_profiles=existing)
    )
    assert len(profiles) == 2
    assert m1.voice_profile_id == "vp_ref"
    assert m2.voice_profile_id != "vp_ref"
    assert profiles[1].is_reference is False
    # 变体音高在合理范围内
    assert 0.5 <= profiles[1].pitch <= 1.5


# ==================== 真实音频特征分析 ====================


def _write_wav(path, samples, sample_rate=16000):
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        pcm = struct.pack("<%dh" % len(samples), *[int(s * 32767) for s in samples])
        wf.writeframes(pcm)


def test_analyze_audio_real_features(tmp_path):
    """正弦波 WAV 的基频估计接近真实频率，能量大于零。"""
    assigner = VoiceProfileAssigner(M06Config())
    sample_rate = 16000
    freq = 200.0
    t = np.arange(sample_rate * 0.5) / sample_rate
    samples = (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    path = tmp_path / "tone.wav"
    _write_wav(path, samples, sample_rate)

    features = asyncio.run(assigner._analyze_audio(str(path)))
    assert features is not None
    assert features["energy_mean"] > 0
    assert features["sample_rate"] == sample_rate
    # 基频估计应接近 200Hz（±15%）
    assert 170 <= features["pitch_mean"] <= 230


def test_analyze_audio_missing_file_returns_none(tmp_path):
    assigner = VoiceProfileAssigner(M06Config())
    assert asyncio.run(assigner._analyze_audio(str(tmp_path / "no.wav"))) is None


def test_voice_parameters_adjust_from_features(tmp_path):
    """真实音频特征驱动音色参数微调。"""
    assigner = VoiceProfileAssigner(M06Config())
    # 低频音 → 音高下调倾向
    sample_rate = 16000
    freq = 90.0
    t = np.arange(sample_rate * 0.4) / sample_rate
    samples = (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    path = tmp_path / "low.wav"
    _write_wav(path, samples, sample_rate)

    features = asyncio.run(assigner._analyze_audio(str(path)))
    params = assigner._generate_voice_parameters(
        {"role_type": "supporting", "gender": "unknown", "age_range": ""},
        features,
    )
    # 低频（90Hz < 180Hz 参考）→ pitch 调整应 < 1.0
    assert params["pitch"] < 1.0
    assert 0.5 <= params["pitch"] <= 1.5
