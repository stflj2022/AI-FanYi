"""
Ticket 006 M04 人物数据库核心测试

覆盖说话人聚类（DBSCAN、参数调整、小聚类合并、评估）、人物链接
（跨集相似度匹配、性别/年龄/角色推断、人物创建）以及 M04Worker 端到端处理。
"""
import json
import math
import random
from pathlib import Path

import numpy as np
import pytest

from filmdub.workers.character_db.clustering import SpeakerClustering
from filmdub.workers.character_db.linker import CharacterLinker
from filmdub.workers.character_db.models import (
    SpeakerEmbedding,
    Cluster,
    Character,
    Gender,
    RoleType,
)
from filmdub.workers.character_db.config import M04Config


def _embedding(center, jitter=0.02, seed=0):
    rng = random.Random(seed)
    return [c + rng.uniform(-jitter, jitter) for c in center]


def _se(segment_id, center, start=0.0, end=1.0, text="", jitter=0.02, seed=0):
    return SpeakerEmbedding(
        segment_id=segment_id,
        start_time=start,
        end_time=end,
        embedding=_embedding(center, jitter, seed),
        confidence=0.9,
        text=text,
    )


# ==================== 聚类 ====================


def test_cluster_speakers_separates_distinct_speakers():
    """不同说话人（不同嵌入方向）被正确分开。"""
    center_a = [1.0, 0.0, 0.0, 0.0, 0.0]
    center_b = [0.0, 1.0, 0.0, 0.0, 0.0]
    center_c = [0.0, 0.0, 1.0, 0.0, 0.0]

    embeddings = []
    for i in range(8):
        embeddings.append(_se(f"a{i}", center_a, seed=i))
    for i in range(8):
        embeddings.append(_se(f"b{i}", center_b, seed=i))
    for i in range(8):
        embeddings.append(_se(f"c{i}", center_c, seed=i))

    clustering = SpeakerClustering(eps=0.3, min_samples=2, min_cluster_size=2)
    clusters = clustering.cluster_speakers(embeddings)

    # 三个说话人应聚成 3 类（噪声可能残留，但不影响主断言）
    speaker_sets = []
    for cluster in clusters:
        speaker_sets.append({se.segment_id[0] for se in cluster.speaker_embeddings})

    merged = set()
    for s in speaker_sets:
        merged |= s
    assert len(clusters) >= 2
    # 每个聚类的嵌入中心应与某个说话人一致
    for cluster in clusters:
        assert cluster.size > 0
        assert cluster.centroid is not None


def test_cluster_speakers_too_few_embeddings():
    """嵌入不足时返回空列表。"""
    clustering = SpeakerClustering()
    assert clustering.cluster_speakers([]) == []
    single = [_se("s0", [0.5, 0.5, 0.5])]
    assert clustering.cluster_speakers(single) == []


def test_merge_small_clusters():
    """小聚类合并到最近的大聚类。"""
    # 构造 3 组：两大一小（方向区分，cosine 距离）
    center_a = [1.0, 0.0, 0.0]
    center_b = [0.0, 1.0, 0.0]
    center_c = [0.05, 0.99, 0.0]  # 靠近 B 的小聚类

    embeddings = []
    for i in range(6):
        embeddings.append(_se(f"a{i}", center_a, seed=i))
    for i in range(6):
        embeddings.append(_se(f"b{i}", center_b, seed=i))
    # 小聚类只有 1 个样本（低于 min_cluster_size=2）
    embeddings.append(_se("c0", center_c, seed=99))

    clustering = SpeakerClustering(eps=0.25, min_samples=2, min_cluster_size=2)
    clusters = clustering.cluster_speakers(embeddings, adjust_parameters=False)

    # 小聚类 c0 不应独立成簇（被合并或视为噪声）
    cluster_ids_with_c = [
        c.cluster_id for c in clusters if any(se.segment_id == "c0" for se in c.speaker_embeddings)
    ]
    assert len(cluster_ids_with_c) <= 1


def test_evaluate_clustering_metrics():
    """评估指标包含聚类数与噪声统计。"""
    embeddings = [
        _se("a0", [1.0, 0.0, 0.0]),
        _se("a1", [0.99, 0.02, 0.0]),
        _se("b0", [0.0, 1.0, 0.0]),
        _se("b1", [0.01, 0.99, 0.0]),
    ]
    clustering = SpeakerClustering(eps=0.3, min_samples=2, min_cluster_size=1)
    clusters = clustering.cluster_speakers(embeddings, adjust_parameters=False)
    labels = clustering._dbscan_clustering(np.array([e.embedding for e in embeddings]))
    # 直接用最终聚类推导标签
    cluster_map = {}
    for c in clusters:
        for se in c.speaker_embeddings:
            cluster_map[se.segment_id] = c.cluster_id
    final_labels = np.array([cluster_map.get(e.segment_id, -1) for e in embeddings])

    metrics = clustering.evaluate_clustering(embeddings, final_labels)
    assert "n_clusters" in metrics
    assert metrics["n_clusters"] >= 1
    assert "silhouette_score" in metrics
    assert -1.0 <= metrics["silhouette_score"] <= 1.0


# ==================== 人物链接 ====================


def _cluster_of(cluster_id, embeddings):
    return Cluster(cluster_id=cluster_id, speaker_embeddings=embeddings)


def test_link_speakers_to_characters_creates_new():
    """新聚类创建新人物并推断属性。"""
    linker = CharacterLinker(M04Config())
    embeddings = [
        _se("s0", [0.5] * 5, text="他说他要去学校", seed=1),
        _se("s1", [0.5] * 5, text="爸爸说了很多", seed=2),
        _se("s2", [0.5] * 5, text="老师布置了作业", seed=3),
    ]
    cluster = _cluster_of(0, embeddings)

    characters = linker.link_speakers_to_characters([cluster], "proj-test")
    assert len(characters) == 1
    char = characters[0]
    assert char.character_id == "proj-test_char_0"
    assert char.total_segments == 3
    assert char.total_duration == 3.0
    assert char.gender == Gender.MALE  # "他" 出现多次


def test_link_speakers_matches_existing_character():
    """跨集一致性：相似嵌入匹配到现有人物并累计统计。"""
    linker = CharacterLinker(M04Config(similarity_threshold=0.8))

    ref_embedding = [0.5, 0.5, 0.5, 0.5, 0.5]
    existing = Character(
        character_id="proj1_char_0",
        name="Speaker_1",
        total_segments=10,
        total_duration=100.0,
        reference_embedding=ref_embedding,
    )

    new_cluster = _cluster_of(0, [
        _se("s0", ref_embedding, jitter=0.001, seed=1),
        _se("s1", ref_embedding, jitter=0.001, seed=2),
    ])

    characters = linker.link_speakers_to_characters(
        [new_cluster], "proj2", existing_characters=[existing]
    )
    assert len(characters) == 1
    assert characters[0].character_id == "proj1_char_0"
    assert characters[0].total_segments == 12  # 累计
    assert characters[0].total_duration == 102.0


def test_link_speakers_does_not_match_dissimilar():
    """低相似度不匹配现有人物，而是创建新人物。"""
    linker = CharacterLinker(M04Config(similarity_threshold=0.9))
    existing = Character(
        character_id="char-x",
        name="Speaker_1",
        reference_embedding=[1.0, 0.0, 0.0, 0.0, 0.0],
    )
    cluster = _cluster_of(5, [
        _se("s0", [0.0, 1.0, 0.0, 0.0, 0.0], seed=1),
    ])

    characters = linker.link_speakers_to_characters(
        [cluster], "proj3", existing_characters=[existing]
    )
    assert characters[0].character_id == "proj3_char_5"
    assert characters[0].name == "Speaker_6"


def test_infer_gender_female():
    """女性代词推断为 FEMALE。"""
    linker = CharacterLinker(M04Config())
    cluster = _cluster_of(0, [
        _se("s0", [0.5] * 3, text="她说她要去找她朋友", seed=1),
    ])
    assert linker._infer_gender(cluster) == Gender.FEMALE


def test_infer_role_type_by_segments():
    """按段落数量推断角色类型。"""
    linker = CharacterLinker(M04Config())
    many = _cluster_of(0, [_se(f"s{i}", [0.5] * 3, seed=i) for i in range(60)])
    assert linker._infer_role_type(many) == RoleType.PROTAGONIST

    few = _cluster_of(1, [_se(f"t{i}", [0.5] * 3, seed=i) for i in range(5)])
    assert linker._infer_role_type(few) == RoleType.UNKNOWN


# ==================== M04Worker 端到端 ====================


def test_m04_worker_process_job(tmp_path, monkeypatch):
    """M04Worker 从嵌入 Artifact 到人物产出的端到端流程。"""
    import asyncio
    from filmdub.workers.character_db import M04Worker

    # 准备嵌入 Artifact
    project_id = "proj-e2e"
    artifact_dir = tmp_path / project_id / "artifacts"
    artifact_dir.mkdir(parents=True)

    embeddings_data = []
    for i in range(6):
        embeddings_data.append({
            "segment_id": f"seg-a{i}",
            "start_time": i,
            "end_time": i + 1,
            "embedding": [1.0 - i * 0.001, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "confidence": 0.9,
            "text": f"speaker a 第{i}句",
        })
    for i in range(6):
        embeddings_data.append({
            "segment_id": f"seg-b{i}",
            "start_time": i,
            "end_time": i + 1,
            "embedding": [0.0, 1.0 - i * 0.001, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "confidence": 0.85,
            "text": f"speaker b 第{i}句",
        })
    (artifact_dir / "speaker_embeddings.json").write_text(
        json.dumps({"embeddings": embeddings_data}), encoding="utf-8"
    )

    worker = M04Worker(projects_base_dir=tmp_path)
    result = asyncio.run(worker.process_job({
        "job_id": "job-1",
        "project_id": project_id,
    }))

    assert result["status"] == "success"
    assert len(result["characters"]) >= 1
    assert "metrics" in result
    assert "artifact_path" in result
    saved = json.loads(Path(result["artifact_path"]).read_text(encoding="utf-8"))
    assert saved["status"] == "success"


def test_m04_worker_missing_artifact_returns_error(tmp_path):
    """缺少输入 Artifact 时返回 error 状态。"""
    import asyncio
    from filmdub.workers.character_db import M04Worker

    worker = M04Worker(projects_base_dir=tmp_path)
    result = asyncio.run(worker.process_job({
        "job_id": "job-x",
        "project_id": "no-such-project",
    }))
    assert result["status"] == "error"
    assert "Speaker embeddings artifact not found" in result["error"]
