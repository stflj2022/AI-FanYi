"""
说话人到人物映射器

将 M05 提取的说话人映射到 M04 识别的人物
"""
import numpy as np
from typing import List, Optional, Dict, Any, Set, Tuple
import logging

logger = logging.getLogger(__name__)

from .models import SpeakerToCharacterMapping, MappingResult
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

    async def map_speakers(
        self,
        speakers: List[Dict[str, Any]],
        characters: List[Dict[str, Any]],
        existing_mappings: Optional[List[Dict[str, Any]]] = None,
        project_metadata: Optional[Dict[str, Any]] = None
    ) -> MappingResult:
        """
        将说话人映射到人物

        Args:
            speakers: 说话人列表（来自 M05）
            characters: 人物列表（来自 M04）
            existing_mappings: 已有映射（跨集一致性）
            project_metadata: 项目元数据

        Returns:
            映射结果
        """
        logger.info(f"Mapping {len(speakers)} speakers to {len(characters)} characters")

        mappings = []
        unmapped_speakers = []
        unmapped_characters = []

        # 1. 尝试使用已有映射（跨集一致性）
        if existing_mappings and self.config.enable_cross_episode_consistency:
            mapped_speakers, mapped_characters = self._apply_existing_mappings(
                speakers,
                characters,
                existing_mappings,
                mappings
            )
        else:
            mapped_speakers = set()
            mapped_characters = set()

        # 2. 对未映射的说话人进行新映射
        remaining_speakers = [
            s for s in speakers
            if s["speaker_id"] not in mapped_speakers
        ]

        remaining_characters = [
            c for c in characters
            if c["character_id"] not in mapped_characters
        ]

        # 3. 计算相似度并找到最佳匹配
        for speaker in remaining_speakers:
            best_match = await self._find_best_match(
                speaker,
                remaining_characters
            )

            if best_match:
                mapping = SpeakerToCharacterMapping(
                    speaker_id=speaker["speaker_id"],
                    character_id=best_match["character_id"],
                    similarity=best_match["similarity"],
                    confidence=best_match["confidence"]
                )
                mappings.append(mapping)

                # 移除已匹配的人物
                remaining_characters = [
                    c for c in remaining_characters
                    if c["character_id"] != best_match["character_id"]
                ]

                mapped_speakers.add(speaker["speaker_id"])
                mapped_characters.add(best_match["character_id"])
            else:
                unmapped_speakers.append(speaker["speaker_id"])

        # 4. 记录未映射的人物
        unmapped_characters = [
            c["character_id"] for c in remaining_characters
        ]

        logger.info(
            f"Mapping completed: {len(mappings)} mapped, "
            f"{len(unmapped_speakers)} unmapped speakers, "
            f"{len(unmapped_characters)} unmapped characters"
        )

        return MappingResult(
            mappings=mappings,
            voice_profiles=[],
            unmapped_speakers=unmapped_speakers,
            unmapped_characters=unmapped_characters
        )

    def _apply_existing_mappings(
        self,
        speakers: List[Dict[str, Any]],
        characters: List[Dict[str, Any]],
        existing_mappings: List[Dict[str, Any]],
        mappings: List[SpeakerToCharacterMapping]
    ) -> Tuple[Set[str], Set[str]]:
        """
        应用已有映射

        Args:
            speakers: 说话人列表
            characters: 人物列表
            existing_mappings: 已有映射
            mappings: 映射列表（输出）

        Returns:
            (已映射的说话人ID集合, 已映射的人物ID集合)
        """
        mapped_speakers = set()
        mapped_characters = set()

        # 创建人物查找表
        character_map = {
            c["character_id"]: c
            for c in characters
        }

        for existing in existing_mappings:
            speaker_id = existing["speaker_id"]
            character_id = existing["character_id"]

            # 检查是否仍然有效
            if character_id not in character_map:
                continue

            # 跨集一致性验证：若说话人带嵌入且人物有参考嵌入，
            # 计算余弦相似度，低于阈值时放弃该已有映射（交由新映射流程处理）
            character = character_map[character_id]
            speaker = next(
                (s for s in speakers if s["speaker_id"] == speaker_id),
                None,
            )
            if speaker and "embedding" in speaker and character.get("reference_embedding"):
                embedding = np.array(speaker["embedding"])
                ref_embedding = np.array(character["reference_embedding"])
                denom = np.linalg.norm(embedding) * np.linalg.norm(ref_embedding)
                if denom == 0:
                    continue
                similarity = float(np.dot(embedding, ref_embedding) / denom)
                if similarity < self.config.similarity_threshold:
                    logger.info(
                        f"Existing mapping {speaker_id}->{character_id} "
                        f"below threshold ({similarity:.3f}), skipped"
                    )
                    continue
                mapping_similarity = similarity
                mapping_confidence = min(
                    existing.get("confidence", 0.0),
                    similarity,
                )
            else:
                mapping_similarity = existing.get("similarity", 0.0)
                mapping_confidence = existing.get("confidence", 0.0)

            # 添加映射
            mapping = SpeakerToCharacterMapping(
                speaker_id=speaker_id,
                character_id=character_id,
                similarity=mapping_similarity,
                confidence=mapping_confidence,
                manual_override=existing.get("manual_override", False),
                notes="从已有映射继承（跨集一致性）",
            )

            mappings.append(mapping)
            mapped_speakers.add(speaker_id)
            mapped_characters.add(character_id)

        logger.info(f"Applied {len(existing_mappings)} existing mappings")

        return mapped_speakers, mapped_characters

    async def _find_best_match(
        self,
        speaker: Dict[str, Any],
        characters: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        为说话人找到最佳匹配的人物

        Args:
            speaker: 说话人信息
            characters: 人物列表

        Returns:
            最佳匹配或 None
        """
        if not characters:
            return None

        # 计算与每个人物的相似度
        similarities = []

        for character in characters:
            similarity, confidence = await self._calculate_similarity(
                speaker,
                character
            )

            if similarity >= self.config.similarity_threshold:
                similarities.append({
                    "character_id": character["character_id"],
                    "character_name": character["name"],
                    "similarity": similarity,
                    "confidence": confidence
                })

        # 返回相似度最高的匹配
        if similarities:
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            return similarities[0]

        return None

    async def _calculate_similarity(
        self,
        speaker: Dict[str, Any],
        character: Dict[str, Any]
    ) -> Tuple[float, float]:
        """
        计算说话人与人物的相似度

        Args:
            speaker: 说话人信息
            character: 人物信息

        Returns:
            (相似度, 置信度)
        """
        similarity_scores = []

        # 1. 基于嵌入的相似度
        if "embedding" in speaker and "reference_embedding" in character:
            embedding = np.array(speaker["embedding"])
            ref_embedding = np.array(character["reference_embedding"])

            # 余弦相似度
            embedding_sim = np.dot(embedding, ref_embedding) / (
                np.linalg.norm(embedding) * np.linalg.norm(ref_embedding)
            )
            similarity_scores.append(("embedding", embedding_sim, 0.4))

        # 2. 基于说话时间的相似度（段落数量和时长）
        if "total_duration" in speaker and "total_duration" in character:
            # 人物的参考时长与说话人时长的比例
            char_duration = character["total_duration"]
            speaker_duration = speaker["total_duration"]

            if char_duration > 0:
                duration_ratio = min(speaker_duration / char_duration, 1.0)
                similarity_scores.append(("duration", duration_ratio, 0.2))

        # 3. 基于角色类型的相似度
        if "role_type" in speaker and "role_type" in character:
            if speaker["role_type"] == character["role_type"]:
                similarity_scores.append(("role_type", 1.0, 0.2))
            else:
                # 根据角色类型之间的相似性给分
                role_similarity = self._calculate_role_similarity(
                    speaker["role_type"],
                    character["role_type"]
                )
                similarity_scores.append(("role_type", role_similarity, 0.2))

        # 4. 基于音频特征的相似度
        if "audio_features" in speaker and "reference_features" in character:
            feature_sim = self._calculate_feature_similarity(
                speaker["audio_features"],
                character["reference_features"]
            )
            similarity_scores.append(("features", feature_sim, 0.2))

        # 加权计算总相似度
        if not similarity_scores:
            return 0.0, 0.0

        total_weight = sum(weight for _, _, weight in similarity_scores)
        weighted_sum = sum(score * weight for _, score, weight in similarity_scores)

        similarity = weighted_sum / total_weight

        # 计算置信度（基于特征数量）
        confidence = min(len(similarity_scores) / 4.0, 1.0)

        return similarity, confidence

    def _calculate_role_similarity(self, role_a: str, role_b: str) -> float:
        """
        计算角色类型相似度

        Args:
            role_a: 角色 A 类型
            role_b: 角色 B 类型

        Returns:
            相似度 (0.0-1.0)
        """
        # 定义角色相似性矩阵
        role_similarity = {
            ("protagonist", "protagonist"): 1.0,
            ("protagonist", "supporting"): 0.7,
            ("protagonist", "minor"): 0.5,
            ("antagonist", "antagonist"): 1.0,
            ("antagonist", "supporting"): 0.6,
            ("supporting", "supporting"): 1.0,
            ("supporting", "minor"): 0.8,
            ("minor", "minor"): 1.0,
            ("narrator", "narrator"): 1.0,
        }

        # 尝试获取相似度
        key1 = (role_a, role_b)
        key2 = (role_b, role_a)

        if key1 in role_similarity:
            return role_similarity[key1]
        elif key2 in role_similarity:
            return role_similarity[key2]
        else:
            return 0.3  # 默认低相似度

    def _calculate_feature_similarity(
        self,
        features_a: Dict[str, Any],
        features_b: Dict[str, Any]
    ) -> float:
        """
        计算音频特征相似度

        Args:
            features_a: 特征 A
            features_b: 特征 B

        Returns:
            相似度 (0.0-1.0)
        """
        similarities = []

        # 音高相似度
        if "pitch_mean" in features_a and "pitch_mean" in features_b:
            pitch_a = features_a["pitch_mean"]
            pitch_b = features_b["pitch_mean"]

            # 归一化差异
            pitch_diff = abs(pitch_a - pitch_b) / max(pitch_a, pitch_b)
            pitch_sim = max(0, 1 - pitch_diff)
            similarities.append(pitch_sim)

        # 能量相似度
        if "energy_mean" in features_a and "energy_mean" in features_b:
            energy_a = features_a["energy_mean"]
            energy_b = features_b["energy_mean"]

            energy_diff = abs(energy_a - energy_b) / max(energy_a, energy_b)
            energy_sim = max(0, 1 - energy_diff)
            similarities.append(energy_sim)

        # 频谱相似度
        if "spectral_centroid_mean" in features_a and "spectral_centroid_mean" in features_b:
            spec_a = features_a["spectral_centroid_mean"]
            spec_b = features_b["spectral_centroid_mean"]

            spec_diff = abs(spec_a - spec_b) / max(spec_a, spec_b)
            spec_sim = max(0, 1 - spec_diff)
            similarities.append(spec_sim)

        return np.mean(similarities) if similarities else 0.0

    def _handle_new_speakers(
        self,
        unmapped_speakers: List[str],
        characters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        处理新说话人（可能是新人物）

        Args:
            unmapped_speakers: 未映射的说话人列表
            characters: 人物列表

        Returns:
            新人物建议列表
        """
        suggestions = []
        for speaker_id in unmapped_speakers:
            suggestions.append({
                "suggested_character_id": f"new_char_{speaker_id}",
                "source_speaker_id": speaker_id,
                "confidence": 0.0,  # 需要人工确认或 M04 重新聚类
                "requires_review": True,
                "reason": "未匹配到现有人物，建议作为新人物候选",
            })
        if suggestions:
            logger.info(
                f"Suggested {len(suggestions)} new character candidates "
                f"for unmapped speakers"
            )
        return suggestions
