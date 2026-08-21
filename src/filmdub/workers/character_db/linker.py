"""
人物链接器

将说话人聚类链接到人物
"""
from typing import List, Optional, Dict, Any
from loguru import logger
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

        Args:
            cluster: 聚类
            existing_characters: 已有的人物列表

        Returns:
            匹配的人物或 None
        """
        if not existing_characters:
            return None

        # 计算聚类质心与每个人物的相似度
        for character in existing_characters:
            # 简化版：基于人物名称和描述匹配
            # 实际实现应该使用嵌入相似度

            # TODO: 使用人物嵌入进行比较
            pass

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
            # TODO: 实际实现
            response = requests.post(
                self.config.llm_endpoint,
                json={
                    "model": self.config.llm_model,
                    "prompt": prompt
                },
                timeout=30
            )

            if response.status_code == 200:
                # 解析响应
                # TODO: 解析 LLM 返回的 JSON
                pass

        except Exception as e:
            logger.warning(f"Failed to analyze character with LLM: {e}")

        return None

    def _infer_gender(self, cluster: Cluster) -> Gender:
        """
        推断性别

        Args:
            cluster: 聚类

        Returns:
            性别
        """
        # 简化版：默认未知
        # 实际实现应该使用语音特征或 LLM 分析文本
        return Gender.UNKNOWN

    def _infer_age_range(self, cluster: Cluster) -> Optional[str]:
        """
        推断年龄段

        Args:
            cluster: 聚类

        Returns:
            年龄段或 None
        """
        # 简化版：默认 None
        # 实际实现应该使用语音特征或 LLM 分析文本
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
