"""
人物链接器

将说话人聚类链接到人物
"""
import json
import re
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)
import requests

from .models import Cluster, Character, CharacterRelationship, Gender, RoleType
from .config import M04Config


class CharacterLinker:
    """人物链接器"""

    def __init__(self, config: M04Config):
        """
        初始化链接器

        Args:
            config: M04 配置
        """
        self.config = config

    def link_speakers_to_characters(
        self,
        clusters: List[Cluster],
        project_id: str,
        existing_characters: Optional[List[Character]] = None
    ) -> List[Character]:
        """
        将说话人聚类链接到人物

        Args:
            clusters: 聚类列表
            project_id: 项目 ID
            existing_characters: 已有的人物列表

        Returns:
            人物列表
        """
        characters = []
        existing_characters = existing_characters or []

        for cluster in clusters:
            # 查找是否有现有人物可以匹配
            character = self._find_existing_character(
                cluster,
                existing_characters
            )

            if character:
                # 更新现有任务人物
                self._update_character_from_cluster(character, cluster)
                characters.append(character)
            else:
                # 创建新人物
                character = self._create_character_from_cluster(
                    cluster,
                    project_id
                )
                characters.append(character)

        logger.info(f"Linked {len(clusters)} clusters to {len(characters)} characters")

        return characters

    def _find_existing_character(
        self,
        cluster: Cluster,
        existing_characters: List[Character]
    ) -> Optional[Character]:
        """
        查找现有人物

        基于聚类质心与人物参考嵌入的余弦相似度匹配，
        相似度超过阈值时返回该人物，实现跨集一致性。

        Args:
            cluster: 聚类
            existing_characters: 已有的人物列表

        Returns:
            匹配的人物或 None
        """
        if not existing_characters:
            return None

        import numpy as np

        centroid = cluster.centroid
        if centroid is None and cluster.speaker_embeddings:
            centroid = np.mean(
                [np.array(se.embedding) for se in cluster.speaker_embeddings],
                axis=0
            )

        best_match = None
        best_similarity = 0.0

        for character in existing_characters:
            if character.reference_embedding is None:
                continue

            ref = np.array(character.reference_embedding)
            if centroid is None or np.linalg.norm(ref) == 0:
                continue

            denom = np.linalg.norm(centroid) * np.linalg.norm(ref)
            similarity = float(np.dot(centroid, ref) / denom) if denom > 0 else 0.0

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = character

        if best_match and best_similarity >= self.config.similarity_threshold:
            logger.info(
                f"Matched cluster to existing character {best_match.name} "
                f"(similarity={best_similarity:.3f})"
            )
            return best_match

        return None

    def _create_character_from_cluster(
        self,
        cluster: Cluster,
        project_id: str
    ) -> Character:
        """
        从聚类创建人物

        Args:
            cluster: 聚类
            project_id: 项目 ID

        Returns:
            人物
        """
        # 生成人物 ID
        character_id = f"{project_id}_char_{cluster.cluster_id}"

        # 默认名称
        name = f"Speaker_{cluster.cluster_id + 1}"

        # 统计信息
        total_duration = sum(
            se.end_time - se.start_time
            for se in cluster.speaker_embeddings
        )

        # 推断属性
        gender = self._infer_gender(cluster)
        age_range = self._infer_age_range(cluster)
        role_type = self._infer_role_type(cluster)

        # 尝试匹配 TMDB 人物
        tmdb_info = self._match_tmdb_character(cluster)
        if tmdb_info:
            name = tmdb_info.get("name", name)

        character = Character(
            character_id=character_id,
            name=name,
            gender=gender,
            age_range=age_range,
            role_type=role_type,
            total_segments=len(cluster.speaker_embeddings),
            total_duration=total_duration,
            confidence=0.0  # 初始置信度
        )

        logger.info(f"Created character: {name} (id={character_id})")

        return character

    def _update_character_from_cluster(
        self,
        character: Character,
        cluster: Cluster
    ):
        """
        从聚类更新人物

        Args:
            character: 人物
            cluster: 聚类
        """
        # 更新统计
        total_duration = sum(
            se.end_time - se.start_time
            for se in cluster.speaker_embeddings
        )

        character.total_segments += len(cluster.speaker_embeddings)
        character.total_duration += total_duration

    def _match_tmdb_character(
        self,
        cluster: Cluster
    ) -> Optional[Dict[str, Any]]:
        """
        匹配 TMDB 人物

        Args:
            cluster: 聚类

        Returns:
            TMDB 人物信息或 None
        """
        if not self.config.tmdb_api_key:
            return None

        # 聚类中的文本
        texts = [se.text for se in cluster.speaker_embeddings if se.text]

        if not texts:
            return None

        # 使用 LLM 分析文本，提取人物信息
        character_info = self._analyze_character_with_llm(texts)

        if character_info:
            return character_info

        return None

    def _analyze_character_with_llm(
        self,
        texts: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 分析文本，提取人物信息

        Args:
            texts: 文本列表

        Returns:
            人物信息或 None
        """
        # 汇总文本
        combined_text = "\n".join(texts[:5])  # 取前 5 条

        # 构建提示词
        prompt = f"""
        分析以下对话文本，识别说话人的信息：
        {combined_text}

        请提取以下信息（JSON 格式）：
        - name: 人物名称
        - gender: 性别
        - age_range: 年龄段
        - role_type: 角色类型
        - description: 人物描述

        如果无法确定，请返回 null。
        """

        try:
            # 调用 LLM API
            response = requests.post(
                self.config.llm_endpoint,
                json={
                    "model": self.config.llm_model,
                    "prompt": prompt
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                # 兼容多种响应格式
                content = data.get("response") or data.get("text") or data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # 提取 JSON 块
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    if parsed.get("name") or parsed.get("gender"):
                        return parsed

        except Exception as e:
            logger.warning(f"Failed to analyze character with LLM: {e}")

        return None

    def _infer_gender(self, cluster: Cluster) -> Gender:
        """
        推断性别

        基于对话文本中的中文性别代词（他/她/它）统计进行启发式推断；
        无法确定时返回 UNKNOWN。

        Args:
            cluster: 聚类

        Returns:
            性别
        """
        texts = [se.text for se in cluster.speaker_embeddings if se.text]
        combined = "".join(texts)

        male_markers = combined.count("他")
        female_markers = combined.count("她")
        # 英文代词（避免误计 she 中的 he）
        male_markers += len(re.findall(r"\bhe\b|\bhim\b|\bhis\b", combined, re.IGNORECASE))
        female_markers += len(re.findall(r"\bshe\b|\bher\b|\bhers\b", combined, re.IGNORECASE))

        total = male_markers + female_markers
        if total == 0:
            return Gender.UNKNOWN

        if male_markers > female_markers * 1.5:
            return Gender.MALE
        if female_markers > male_markers * 1.5:
            return Gender.FEMALE

        return Gender.UNKNOWN

    def _infer_age_range(self, cluster: Cluster) -> Optional[str]:
        """
        推断年龄段

        基于对话文本中的年龄/称呼关键词进行启发式推断。

        Args:
            cluster: 聚类

        Returns:
            年龄段或 None
        """
        texts = [se.text for se in cluster.speaker_embeddings if se.text]
        combined = "".join(texts)

        child_patterns = [r"孩子", r"小朋友", r"妈妈", r"爸爸", r"作业", r"学校"]
        elder_patterns = [r"老了", r"年轻时", r"退休", r"爷爷", r"奶奶", r"孙子"]
        teen_patterns = [r"上学", r"同学", r"老师", r"考试"]

        if any(re.search(p, combined) for p in child_patterns):
            return "child"
        if any(re.search(p, combined) for p in teen_patterns):
            return "teen"
        if any(re.search(p, combined) for p in elder_patterns):
            return "senior"

        return None

    def _infer_role_type(self, cluster: Cluster) -> RoleType:
        """
        推断角色类型

        Args:
            cluster: 聚类

        Returns:
            角色类型
        """
        # 简化版：根据段落数量推断
        segment_count = len(cluster.speaker_embeddings)

        if segment_count > 50:
            return RoleType.PROTAGONIST
        elif segment_count > 20:
            return RoleType.SUPPORTING
        elif segment_count > 10:
            return RoleType.MINOR
        else:
            return RoleType.UNKNOWN
