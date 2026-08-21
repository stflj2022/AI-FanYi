"""
Ticket 007 M04 人物关系构建测试

覆盖交互发现（提及检测）、关键词关系推断（家庭/朋友/敌人/同事/师徒）、
端到端关系构建（LLM 不可用时回退关键词）与关系图构建（对称边）。
"""
import json

import pytest

from filmdub.workers.character_db.models import Character, Gender, RoleType
from filmdub.workers.character_db.relationships import (
    RelationshipBuilder,
    RelationshipType,
)


def _char(character_id, name):
    return Character(
        character_id=character_id,
        name=name,
        gender=Gender.UNKNOWN,
        role_type=RoleType.UNKNOWN,
    )


@pytest.fixture
def builder():
    return RelationshipBuilder(llm_endpoint="http://127.0.0.1:1", llm_model="test")


# ==================== 交互发现 ====================


def test_find_interactions_detects_mentions(builder):
    """A 的对话提及 B 的名字时记录交互。"""
    char_a = _char("c1", "小明")
    char_b = _char("c2", "小红")

    dialogues = [
        {"speaker_id": "c1", "text": "小红，我们今天去哪里？"},
        {"speaker_id": "c1", "text": "天气不错"},
        {"speaker_id": "c2", "text": "随便你"},
    ]

    interactions = builder._find_interactions([char_a, char_b], dialogues)
    assert ("c1", "c2") in interactions
    assert len(interactions[("c1", "c2")]) == 1
    assert "小红" in interactions[("c1", "c2")][0]


def test_find_interactions_no_mention_no_interaction(builder):
    """无提及则无交互。"""
    char_a = _char("c1", "小明")
    char_b = _char("c2", "小红")

    dialogues = [
        {"speaker_id": "c1", "text": "今天天气不错"},
        {"speaker_id": "c2", "text": "是的"},
    ]

    interactions = builder._find_interactions([char_a, char_b], dialogues)
    assert interactions == {}


def test_mentions_character(builder):
    assert builder._mentions_character("小红你等等", "小红") is True
    assert builder._mentions_character("小红你等等", "小明") is False
    assert builder._mentions_character("", "小红") is False


# ==================== 关键词推断 ====================


def test_infer_family_from_keywords(builder):
    rtype, conf = builder._infer_from_keywords("爸爸，我今天放学了")
    assert rtype == RelationshipType.FAMILY
    assert conf >= 0.7


def test_infer_enemy_from_keywords(builder):
    rtype, conf = builder._infer_from_keywords("你这个敌人，我不会放过你的")
    assert rtype == RelationshipType.ENEMY


def test_infer_mentor_from_keywords(builder):
    rtype, _ = builder._infer_from_keywords("师父，请您教我武功")
    assert rtype == RelationshipType.MENTOR


def test_infer_none_when_no_keyword(builder):
    assert builder._infer_from_keywords("今天天气很好，我们走吧") is None


# ==================== LLM 提示与解析 ====================


def test_build_relationship_prompt_contains_names(builder):
    char_a = _char("c1", "小明")
    char_b = _char("c2", "小红")
    prompt = builder._build_relationship_prompt(char_a, char_b, "对话内容")
    assert "小明" in prompt
    assert "小红" in prompt
    assert "relationship_type" in prompt


def test_parse_llm_response_json_block(builder):
    resp = '```json\n{"relationship_type": "friend", "confidence": 0.9, "description": "老友"}\n```'
    parsed = builder._parse_llm_response(resp)
    assert parsed["relationship_type"] == "friend"
    assert parsed["confidence"] == 0.9


def test_parse_llm_response_invalid_returns_none(builder):
    assert builder._parse_llm_response("not json at all") is None


# ==================== 端到端构建 ====================


def test_build_relationships_family_keyword(builder):
    """端到端：提及+关键词 → 家庭关系（LLM 不可达时走关键词路径）。"""
    char_a = _char("c1", "爸爸")
    char_b = _char("c2", "小明")

    dialogues = [
        {"speaker_id": "c2", "text": "爸爸，我放学回来了"},
        {"speaker_id": "c2", "text": "爸爸今天累不累"},
    ]

    import asyncio
    relationships = asyncio.run(
        builder.build_relationships([char_a, char_b], dialogues)
    )
    assert len(relationships) == 1
    rel = relationships[0]
    assert rel.relationship_type == RelationshipType.FAMILY
    assert rel.confidence >= 0.7


def test_build_relationships_no_interaction_none(builder):
    """无交互时不产生关系。"""
    char_a = _char("c1", "甲")
    char_b = _char("c2", "乙")
    dialogues = [{"speaker_id": "c1", "text": "独自思考"}]

    import asyncio
    relationships = asyncio.run(
        builder.build_relationships([char_a, char_b], dialogues)
    )
    assert relationships == []


def test_build_relationships_llm_fallback_when_keyword_misses(builder):
    """关键词不命中时，LLM 不可达 → 返回空（不崩溃）。"""
    char_a = _char("c1", "张三")
    char_b = _char("c2", "李四")
    dialogues = [
        {"speaker_id": "c1", "text": "李四，我们明天见"},
    ]

    import asyncio
    relationships = asyncio.run(
        builder.build_relationships([char_a, char_b], dialogues)
    )
    # LLM 端点不可达 + 无关键词 → 无关系（但流程不抛异常）
    assert relationships == []


# ==================== 关系图 ====================


def test_build_relationship_graph_symmetric(builder):
    """关系图包含对称边。"""
    from filmdub.workers.character_db.models import CharacterRelationship

    rel = CharacterRelationship(
        from_character_id="c1",
        to_character_id="c2",
        relationship_type=RelationshipType.FRIEND,
        confidence=0.8,
        description="好友",
    )
    graph = builder.build_relationship_graph([rel])

    assert "c1" in graph
    assert "c2" in graph
    assert any(e["to"] == "c2" and e["type"] == RelationshipType.FRIEND for e in graph["c1"])
    assert any(e["to"] == "c1" and e["type"] == RelationshipType.FRIEND for e in graph["c2"])
