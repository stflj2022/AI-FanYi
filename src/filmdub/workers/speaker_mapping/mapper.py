"""
说话人到人物的映射器

基于嵌入相似度和上下文信息将说话人映射到人物
"""
import numpy as np
from typing import List, Optional, Dict, Any
from loguru import logger

from .models import SpeakerToCharacterMapping, MappingStatus, MappingResult
from .config import M06Config


class SpeakerToCharacterMapper:
    """说话人到人物映射器"""

    def __init__(self, config: M06Config = None):
        """
        初始化映射器

        Args:
            config: M06 配置
        """
        self.config = config or M06Config()

    def map_speakers(
        self,
        speaker_embeddings: List[Dict[str, Any]],
        characters: List[Dict[str, Any]],
        existing_profiles: Optional[List[Dict[str, Any]]] = None
    ) -> MappingResult:
        """
        将说话人映射到人物

        Args:
            speaker_embeddings: 说话人嵌入列表
                [{"speaker_id": str, "embedding": List[float], ...}]
            characters: 人物列表
                [{"character_id": str, "name": str, "tmdb_id": int, ...}]
            existing_profiles: 已有音色档案
                [{"character_id": str, "embedding": List[float], ...}]

        Returns:
            映射结果
        """
        logger.info(
            f"Mapping {len(speaker_embeddings)} speakers to "
            f"{len(characters)} characters"
        )

        mappings = []
        used_character_ids = set()

        # 1. 计算每个说话人与每个人物的相似度
        for speaker_info in speaker_embeddings:
            speaker_id = speaker_info["speaker_id"]
            speaker_embedding = np.array(speaker_info["embedding"])

            # 找到最佳匹配
            best_match = self._find_best_match(
                speaker_embedding,
                characters,
                existing_profiles,
                used_character_ids
            )

            if best_match:
                # 确定状态
                status = self._determine_status(
                    best_match["similarity"],
                    best_match["confidence"]
                )

                mapping = SpeakerToCharacterMapping(
                    speaker_id=speaker_id,
                    character_id=best_match["character_id"],
                    similarity=best_match["similarity"],
                    confidence=best_match["confidence"],
                    status=status,
                    metadata=best_match.get("metadata")
                )

                mappings.append(mapping)
                used_character_ids.add(best_match["character_id"])
            else:
                # 没有匹配，需要创建新人物
                logger.warning(f"No match found for speaker {speaker_id}")

                # TODO: 创建新人物
                # 这里应该创建一个临时人物 ID
                temp_character_id = f"temp_{speaker_id}"

                mapping = SpeakerToCharacterMapping(
                    speaker_id=speaker_id,
                    character_id=temp_character_id,
                    similarity=0.0,
                    confidence=0.0,
                    status=MappingStatus.MANUAL_REVIEW,
                    metadata={"reason": "no_match_found"}
                )

                mappings.append(mapping)

        # 2. 处理未映射的人物（新说话人）
        self._handle_unmapped_characters(characters, used_character_ids, mappings)

        # 3. 统计
        num_auto_confirmed = sum(
            1 for m in mappings if m.status == MappingStatus.AUTO_CONFIRMED
        )
        num_manual_review = sum(
            1 for m in mappings if m.status == MappingStatus.MANUAL_REVIEW
        )

        result = MappingResult(
            mappings=mappings,
            voice_assignments=[],  # 由 VoiceProfileAssigner 填充
            num_speakers=len(speaker_embeddings),
            num_characters=len(characters),
            num_auto_confirmed=num_auto_confirmed,
            num_manual_review=num_manual_review
        )

        logger.info(
            f"Mapping completed: {num_auto_confirmed} auto-confirmed, "
            f"{num_manual_review} manual review"
        )

        return result

    def _find_best_match(
        self,
        speaker_embedding: np.ndarray,
        characters: List[Dict[str, Any]],
        existing_profiles: Optional[List[Dict[str, Any]]],
        used_character_ids: set
    ) -> Optional[Dict[str, Any]]:
        """
        找到最佳匹配

        Args:
            speaker_embedding: 说话人嵌入
            characters: 人物列表
            existing_profiles: 已有音色档案
            used_character_ids: 已使用的人物 ID

        Returns:
            最佳匹配或 None
        """
        best_match = None
        best_similarity = -1.0

        for character in characters:
            character_id = character["character_id"]

            # 跳过已使用的人物
            if character_id in used_character_ids:
                continue

            # 计算相似度
            similarity, confidence = self._calculate_similarity(
                speaker_embedding,
                character,
                existing_profiles
            )

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = {
                    "character_id": character_id,
                    "similarity": similarity,
                    "confidence": confidence,
                    "metadata": {
                        "character_name": character.get("name"),
                        "tmdb_id": character.get("tmdb_id")
                    }
                }

        # 检查是否达到阈值
        if best_match and best_similarity >= self.config.voice_similarity_threshold:
            return best_match

        return None

    def _calculate_similarity(
        self,
        speaker_embedding: np.ndarray,
        character: Dict[str, Any],
        existing_profiles: Optional[List[Dict[str, Any]]]
    ) -> tuple[float, float]:
        """
        计算相似度

        Args:
            speaker_embedding: 说话人嵌入
            character: 人物信息
            existing_profiles: 已有音色档案

        Returns:
            (相似度, 置信度)
        """
        similarity = 0.0
        confidence = 0.5

        # 1. 如果有现有音色档案，使用档案嵌入计算
        if existing_profiles:
            character_profiles = [
                p for p in existing_profiles
                if p["character_id"] == character["character_id"]
            ]

            if character_profiles:
                # 使用最新的档案
                profile = character_profiles[-1]
                profile_embedding = np.array(profile["embedding"])

                # 计算余弦相似度
                similarity = self._cosine_similarity(
                    speaker_embedding,
                    profile_embedding
                )
                confidence = 0.9  # 基于历史档案，置信度较高

                # 检查跨集一致性
                if self.config.enable_cross_episode_consistency:
                    consistency_score = self._check_cross_episode_consistency(
                        speaker_embedding,
                        character_profiles
                    )
                    similarity = max(similarity, consistency_score)

        # 2. 如果没有档案，使用基础特征匹配（简化版）
        if similarity == 0.0:
            # TODO: 使用 TMDB 信息、文本上下文等进行匹配
            # 临时实现：使用随机相似度
            import random
            similarity = random.uniform(0.3, 0.7)
            confidence = 0.3

        return similarity, confidence

    def _cosine_similarity(
        self,
        vec1: np.ndarray,
        vec2: np.ndarray
    ) -> float:
        """计算余弦相似度"""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def _check_cross_episode_consistency(
        self,
        speaker_embedding: np.ndarray,
        character_profiles: List[Dict[str, Any]]
    ) -> float:
        """
        检查跨集一致性

        Args:
            speaker_embedding: 说话人嵌入
            character_profiles: 人物的所有档案

        Returns:
            一致性分数
        """
        if len(character_profiles) < 2:
            return 0.0

        # 计算与所有档案的相似度
        similarities = []

        for profile in character_profiles:
            profile_embedding = np.array(profile["embedding"])
            similarity = self._cosine_similarity(
                speaker_embedding,
                profile_embedding
            )
            similarities.append(similarity)

        # 计算平均相似度
        avg_similarity = np.mean(similarities)

        # 计算方差（一致性）
        variance = np.var(similarities)
        consistency_score = avg_similarity * (1 - variance)

        return float(consistency_score)

    def _determine_status(
        self,
        similarity: float,
        confidence: float
    ) -> MappingStatus:
        """
        确定映射状态

        Args:
            similarity: 相似度
            confidence: 置信度

        Returns:
            映射状态
        """
        # 高相似度 + 高置信度 = 自动确认
        if similarity >= self.config.consistency_threshold and confidence >= 0.8:
            return MappingStatus.AUTO_CONFIRMED

        # 中等相似度 = 人工审核
        if similarity >= self.config.voice_similarity_threshold:
            return MappingStatus.MANUAL_REVIEW

        # 低相似度 = 失败
        return MappingStatus.FAILED

    def _handle_unmapped_characters(
        self,
        characters: List[Dict[str, Any]],
        used_character_ids: set,
        mappings: List[SpeakerToCharacterMapping]
    ):
        """
        处理未映射的人物

        Args:
            characters: 人物列表
            used_character_ids: 已使用的人物 ID
            mappings: 映射列表
        """
        unmapped = [
            c for c in characters
            if c["character_id"] not in used_character_ids
        ]

        if unmapped:
            logger.warning(
                f"{len(unmapped)} characters not mapped: "
                f"{[c['character_id'] for c in unmapped]}"
            )
