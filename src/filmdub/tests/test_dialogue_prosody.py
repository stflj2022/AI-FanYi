"""
Ticket 010 M07 对白智能 + M08 韵律规划测试

覆盖：
- M07：术语库加载与替换、文化本地化（真实单位换算）、角色语气调整、置信度
- M08：情绪映射、语速/音高/音量计算（含真实音频特征微调）、停顿/重音、置信度
"""
import asyncio
import json

import pytest

from filmdub.workers.dialogue_intelligence.processor import DialogueIntelligence
from filmdub.workers.dialogue_intelligence.config import M07Config
from filmdub.workers.dialogue_intelligence.models import TerminologyEntry
from filmdub.workers.prosody_planning.planner import ProsodyPlanner
from filmdub.workers.prosody_planning.config import M08Config
from filmdub.workers.prosody_planning.models import ProsodyParams


def _character(character_id="C1", name="小明", role_type="protagonist"):
    return {
        "character_id": character_id,
        "name": name,
        "gender": "male",
        "role_type": role_type,
    }


# ==================== M07 术语一致性 ====================


def test_load_terminology_from_file(tmp_path):
    """术语库从 JSON 文件加载。"""
    path = tmp_path / "terms.json"
    path.write_text(json.dumps({
        "福尔摩斯": {"translation": "夏洛克·福尔摩斯", "category": "character", "context": "推理"},
        "卷福": "夏洛克·福尔摩斯",
    }, ensure_ascii=False), encoding="utf-8")

    proc = DialogueIntelligence(M07Config(terminology_file=str(path)))
    assert len(proc.terminology_db) == 2
    assert proc.terminology_db["福尔摩斯"].translation == "夏洛克·福尔摩斯"
    assert proc.terminology_db["卷福"].category == "general"


def test_check_terminology_replaces_terms(tmp_path):
    """术语替换并记录变更。"""
    path = tmp_path / "terms.json"
    path.write_text(json.dumps({"卷福": "夏洛克"}), encoding="utf-8")
    proc = DialogueIntelligence(M07Config(terminology_file=str(path)))

    text, changes = asyncio.run(proc._check_terminology("卷福来了"))
    assert text == "夏洛克来了"
    assert len(changes) == 1
    assert changes[0]["original"] == "卷福"


def test_check_terminology_longest_match_first(tmp_path):
    """长术语优先匹配。"""
    path = tmp_path / "terms.json"
    path.write_text(json.dumps({"福尔摩斯": "福尔摩斯", "夏洛克·福尔摩斯": "夏洛克"}), encoding="utf-8")
    proc = DialogueIntelligence(M07Config(terminology_file=str(path)))
    # "夏洛克·福尔摩斯" 应整体替换，而不是先被 "福尔摩斯" 部分替换
    text, changes = asyncio.run(proc._check_terminology("夏洛克·福尔摩斯来了"))
    assert text == "夏洛克来了"


# ==================== M07 文化本地化 ====================


def test_localize_culture_unit_conversion():
    """英里/华氏度/英寸真实换算。"""
    proc = DialogueIntelligence(M07Config())
    text, adaptations = asyncio.run(proc._localize_culture("开车10英里，气温90华氏度", _character()))
    assert "公里" in text
    assert "摄氏度" in text
    assert "英里" not in text and "华氏度" not in text
    assert len(adaptations) == 2
    # 10 英里 ≈ 16.09 公里
    assert "16" in text


def test_localize_culture_no_match_unchanged():
    proc = DialogueIntelligence(M07Config())
    text, adaptations = asyncio.run(proc._localize_culture("我们走吧", _character()))
    assert text == "我们走吧"
    assert adaptations == []


# ==================== M07 语气调整 ====================


def test_adjust_tone_protagonist_removes_fillers():
    """主角去除口语填充词。"""
    proc = DialogueIntelligence(M07Config())
    text, adjustments = asyncio.run(proc._adjust_tone("嗯，那个，我们出发吧", _character(role_type="protagonist")))
    assert "嗯" not in text and "那个" not in text
    assert text.endswith("。")  # "吧" → "。"
    assert len(adjustments) >= 2


def test_adjust_tone_antagonist():
    """反派去除礼貌用语。"""
    proc = DialogueIntelligence(M07Config())
    text, adjustments = asyncio.run(proc._adjust_tone("请把东西交出来，好吗？", _character(role_type="antagonist")))
    assert "请" not in text
    assert text.endswith("！")
    assert len(adjustments) >= 2


def test_adjust_tone_narrator_removes_interjections():
    proc = DialogueIntelligence(M07Config())
    text, adjustments = asyncio.run(proc._adjust_tone("哎，天亮了", _character(role_type="narrator")))
    assert "哎" not in text
    assert text == "天亮了"


# ==================== M07 端到端 ====================


def test_process_dialogue_full_pipeline(tmp_path):
    """术语+文化+语气全流程处理。"""
    path = tmp_path / "terms.json"
    path.write_text(json.dumps({"卷福": "夏洛克"}), encoding="utf-8")
    proc = DialogueIntelligence(M07Config(terminology_file=str(path)))

    dialogue = {
        "dialogue_id": "d1",
        "text": "嗯，卷福开车10英里来找我",
        "character_id": "C1",
        "speaker_id": "S1",
        "start_time": 0.0,
        "end_time": 2.0,
    }
    processed = asyncio.run(proc.process_dialogue(dialogue, [_character(role_type="protagonist")]))
    assert processed is not None
    assert "夏洛克" in processed.processed_text
    assert "公里" in processed.processed_text
    assert "嗯" not in processed.processed_text
    assert processed.confidence > 0
    assert processed.needs_manual_review is not None


def test_process_dialogue_missing_character_returns_none():
    proc = DialogueIntelligence(M07Config())
    dialogue = {"text": "你好", "character_id": "NOPE", "speaker_id": "S1"}
    assert asyncio.run(proc.process_dialogue(dialogue, [_character()])) is None


def test_process_dialogue_empty_text_returns_none():
    proc = DialogueIntelligence(M07Config())
    assert asyncio.run(proc.process_dialogue({"text": "", "character_id": "C1"}, [_character()])) is None


# ==================== M08 韵律规划 ====================


def _vp(voice_profile_id="vp1", emotion="neutral", pitch=1.0, volume=1.0):
    return {"voice_profile_id": voice_profile_id, "emotion": emotion, "pitch": pitch, "volume": volume}


def _dialogue(text="你好世界", emotion="neutral", duration=2.0):
    return {
        "dialogue_id": "d1",
        "text": text,
        "character_id": "C1",
        "speaker_id": "S1",
        "voice_profile_id": "vp1",
        "emotion": emotion,
        "start_time": 0.0,
        "end_time": duration,
    }


def test_plan_dialogue_basic():
    """中性情绪 → 韵律参数在合理范围。"""
    planner = ProsodyPlanner(M08Config())
    prepared = asyncio.run(planner.plan_dialogue(_dialogue(), [_vp()]))
    assert prepared is not None
    assert prepared.prosody.emotion == "neutral"
    assert 0.5 <= prepared.prosody.speed <= 2.0
    assert 0.5 <= prepared.prosody.pitch <= 2.0
    assert 0.5 <= prepared.prosody.volume <= 1.5


def test_plan_dialogue_emotion_mapping():
    """情绪映射生效：angry 语速/音量 > neutral。"""
    planner = ProsodyPlanner(M08Config())
    # 10 字 / 2s = 5 字/秒 = 标准语速，避免被上下限钳制
    long_text = "我们今天必须把这个问题彻底解决掉然后立刻出发"
    angry = asyncio.run(planner.plan_dialogue(_dialogue(text=long_text, emotion="angry", duration=2.0), [_vp()]))
    neutral = asyncio.run(planner.plan_dialogue(_dialogue(text=long_text, emotion="neutral", duration=2.0), [_vp()]))
    assert angry.prosody.speed > neutral.prosody.speed
    assert angry.prosody.volume > neutral.prosody.volume
    assert angry.prosody.emotion == "angry"


def test_plan_dialogue_missing_voice_profile_returns_none():
    planner = ProsodyPlanner(M08Config())
    assert asyncio.run(planner.plan_dialogue(_dialogue(), [_vp("other")])) is None


def test_calculate_pauses():
    """句末与分句标点位置被识别。"""
    planner = ProsodyPlanner(M08Config())
    pauses = planner._calculate_pauses("你好。我们去，好吗？")
    assert 3 in pauses  # "。"后
    assert 7 in pauses  # "，"后
    assert pauses[-1] == len("你好。我们去，好吗？")  # "？"后


def test_calculate_stresses():
    """强调词后的字符被标记为重音。"""
    planner = ProsodyPlanner(M08Config())
    stresses = planner._calculate_stresses("我真的很厉害")
    assert any(s > 0 for s in stresses)


def test_plan_prosody_audio_feature_pitch_adjust():
    """真实音频特征微调音高：低基频音频 → 音高下调。"""
    planner = ProsodyPlanner(M08Config())
    prosody = asyncio.run(planner._plan_prosody_params(
        _dialogue(),
        _vp(pitch=1.0),
        {"pitch_mean": 90.0, "rms": 0.3},
        original_duration=2.0,
    ))
    # 90Hz < 180Hz 参考 → pitch < 1.0（无情绪加成时）
    assert prosody.pitch < 1.0


def test_plan_prosody_audio_feature_volume_adjust():
    """高 RMS 音频 → 音量下调（避免削波）。"""
    planner = ProsodyPlanner(M08Config())
    prosody = asyncio.run(planner._plan_prosody_params(
        _dialogue(),
        _vp(volume=1.0),
        {"pitch_mean": 180.0, "rms": 0.9},
        original_duration=2.0,
    ))
    assert prosody.volume < 1.0


def test_calculate_confidence_clamps():
    """置信度在 0-1 之间。"""
    planner = ProsodyPlanner(M08Config())
    good = ProsodyParams(speed=1.0, pitch=1.0, volume=1.0, emotion="neutral")
    assert 0.0 <= planner._calculate_confidence(good) <= 1.0
