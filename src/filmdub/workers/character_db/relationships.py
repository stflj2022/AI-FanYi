"""
人物关系构建模块

从对白中推断人物关系并构建关系图
"""
import json
import re
from typing import List, Dict, Any, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)

from .models import Character, CharacterRelationship


class RelationshipType:
    """关系类型"""
    FAMILY = "family"           # 家庭关系（父母、子女、兄弟姐妹等）
    FRIEND = "friend"           # 朋友
    ENEMY = "enemy"             # 敌人
    COLLEAGUE = "colleague"     # 同事
    ROMANTIC = "romantic"       # 恋人/配偶
    MENTOR = "mentor"           # 师徒
    SUBORDINATE = "subordinate" # 上下级
    ACQUAINTANCE = "acquaintance"  # 熟人
    OTHER = "other"             # 其他


class RelationshipBuilder:
    """人物关系构建器"""

    def __init__(self, llm_endpoint: str = "http://localhost:8000", llm_model: str = "qwen"):
        """
        初始化关系构建器

        Args:
            llm_endpoint: LLM 端点
            llm_model: LLM 模型
        """
        self.llm_endpoint = llm_endpoint
        self.llm_model = llm_model

        # 关系关键词模式
        self._init_relationship_patterns()

    def _init_relationship_patterns(self):
        """初始化关系关键词模式"""
        self.family_patterns = [
            r"(父亲|爸爸|爹|老爸|老爹)",
            r"(母亲|妈妈|娘|老妈|老娘)",
            r"(儿子|儿子|小子|小家伙)",
            r"(女儿|闺女|丫头|小棉袄)",
            r"(兄弟|哥哥|弟弟|大哥|二弟|兄长|弟弟)",
            r"(姐妹|姐姐|妹妹|大姐|小妹)",
            r"(爷爷|奶奶|外公|外婆|爷爷|奶奶)",
            r"(叔叔|阿姨|舅舅|姑姑|伯父)",
            r"(丈夫|老公|老婆|妻子|媳妇)",
            r"(老公|老婆|媳妇|老公)",
        ]

        self.friend_patterns = [
            r"(朋友|哥们|兄弟|姐们|闺蜜)",
            r"(老友|好友|密友)",
            r"(同窗|同学|校友)",
            r"(搭档|伙伴)",
        ]

        self.enemy_patterns = [
            r"(敌人|仇人|死敌)",
            r"(对手|竞争者)",
            r"(敌人|仇敌)",
        ]

        self.colleague_patterns = [
            r"(同事|同僚)",
            r"(老板|上司|领导|经理)",
            r"(下属|员工|部下)",
            r"(合伙人|搭档)",
        ]

        self.mentor_patterns = [
            r"(师父|师傅|老师|导师)",
            r"(徒弟|学生|弟子)",
            r"(老师|教授|讲师)",
        ]

    async def build_relationships(
        self,
        characters: List[Character],
        dialogues: List[Dict[str, Any]]
    ) -> List[CharacterRelationship]:
        """
        构建人物关系

        Args:
            characters: 人物列表
            dialogues: 对话列表，每个对话包含 speaker_id 和 text

        Returns:
            人物关系列表
        """
        logger.info(f"Building relationships for {len(characters)} characters")

        # 1. 查找人物交互
        interactions = self._find_interactions(characters, dialogues)

        # 2. 推断关系
        relationships = []

        for char_a, char_b in interactions:
            # 推断关系
            relationship = await self._infer_relationship(
                char_a,
                char_b,
                interactions[(char_a, char_b)]
            )

            if relationship:
                relationships.append(relationship)

        logger.info(f"Built {len(relationships)} relationships")

        return relationships

    def _find_interactions(
        self,
        characters: List[Character],
        dialogues: List[Dict[str, Any]]
    ) -> Dict[Tuple[str, str], List[str]]:
        """
        查找人物交互

        Args:
            characters: 人物列表
            dialogues: 对话列表

        Returns:
            交互字典: {(char_a_id, char_b_id): [对话文本列表]}
        """
        # 创建人物名称集合（用于提及检测）
        character_names = {c.character_id: c.name for c in characters}

        # 按说话人分组对话
        dialogues_by_speaker: Dict[str, List[Dict[str, Any]]] = {}
        for dialogue in dialogues:
            speaker_id = dialogue.get("speaker_id")
            if speaker_id:
                if speaker_id not in dialogues_by_speaker:
                    dialogues_by_speaker[speaker_id] = []
                dialogues_by_speaker[speaker_id].append(dialogue)

        # 查找交互
        interactions: Dict[Tuple[str, str], List[str]] = {}

        for char_a_id, char_a_dialogues in dialogues_by_speaker.items():
            for char_b_id in character_names.keys():
                if char_a_id == char_b_id:
                    continue

                # 查找 char_a 提及 char_b 的对话
                mentions = []

                for dialogue in char_a_dialogues:
                    text = dialogue.get("text", "")

                    # 检查是否提及对方
                    if self._mentions_character(text, character_names[char_b_id]):
                        mentions.append(text)

                # 如果有提及，记录交互
                if mentions:
                    # 确保顺序一致（小 ID 在前）
                    key = tuple(sorted([char_a_id, char_b_id]))
                    if key not in interactions:
                        interactions[key] = []
                    interactions[key].extend(mentions)

        logger.info(f"Found {len(interactions)} character interactions")

        return interactions

    def _mentions_character(self, text: str, character_name: str) -> bool:
        """
        检查文本是否提及某人

        Args:
            text: 文本
            character_name: 人物名称

        Returns:
            是否提及
        """
        if not text or not character_name:
            return False

        # 简单匹配：名称出现在文本中
        return character_name in text

    async def _infer_relationship(
        self,
        char_a: Character,
        char_b: Character,
        interaction_texts: List[str]
    ) -> Optional[CharacterRelationship]:
        """
        推断两个人物之间的关系

        Args:
            char_a: 人物 A
            char_b: 人物 B
            interaction_texts: 交互文本列表

        Returns:
            人物关系或 None
        """
        # 合并交互文本
        combined_text = "\n".join(interaction_texts[:10])  # 限制文本数量

        # 1. 基于关键词快速判断
        keyword_result = self._infer_from_keywords(combined_text)
        if keyword_result:
            return CharacterRelationship(
                from_character_id=char_a.character_id,
                to_character_id=char_b.character_id,
                relationship_type=keyword_result[0],
                confidence=keyword_result[1],
                description=f"基于关键词推断: {keyword_result[0]}"
            )

        # 2. 使用 LLM 推断
        llm_result = await self._infer_with_llm(
            char_a,
            char_b,
            combined_text
        )

        if llm_result:
            return CharacterRelationship(
                from_character_id=char_a.character_id,
                to_character_id=char_b.character_id,
                relationship_type=llm_result.get("type", RelationshipType.OTHER),
                confidence=llm_result.get("confidence", 0.5),
                description=llm_result.get("description", "")
            )

        return None

    def _infer_from_keywords(self, text: str) -> Optional[Tuple[str, float]]:
        """
        基于关键词推断关系

        Args:
            text: 文本

        Returns:
            (关系类型, 置信度) 或 None
        """
        # 检查各种关系类型
        if self._match_patterns(text, self.family_patterns):
            return (RelationshipType.FAMILY, 0.8)

        if self._match_patterns(text, self.friend_patterns):
            return (RelationshipType.FRIEND, 0.75)

        if self._match_patterns(text, self.enemy_patterns):
            return (RelationshipType.ENEMY, 0.8)

        if self._match_patterns(text, self.colleague_patterns):
            return (RelationshipType.COLLEAGUE, 0.7)

        if self._match_patterns(text, self.mentor_patterns):
            return (RelationshipType.MENTOR, 0.75)

        return None

    def _match_patterns(self, text: str, patterns: List[str]) -> bool:
        """匹配模式"""
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        return False

    async def _infer_with_llm(
        self,
        char_a: Character,
        char_b: Character,
        text: str
    ) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 推断关系

        Args:
            char_a: 人物 A
            char_b: 人物 B
            text: 交互文本

        Returns:
            推断结果或 None
        """
        # 构建 LLM 提示
        prompt = self._build_relationship_prompt(char_a, char_b, text)

        try:
            # 调用 LLM API
            # TODO: 实际实现 LLM 调用
            response = await self._call_llm(prompt)

            if response:
                return self._parse_llm_response(response)

        except Exception as e:
            logger.warning(f"Failed to infer relationship with LLM: {e}")

        return None

    def _build_relationship_prompt(
        self,
        char_a: Character,
        char_b: Character,
        text: str
    ) -> str:
        """
        构建 LLM 提示

        Args:
            char_a: 人物 A
            char_b: 人物 B
            text: 交互文本

        Returns:
            提示文本
        """
        return f"""
你是一个影视分析专家。请根据以下对话内容，推断两个角色之间的关系。

角色 A: {char_a.name}
  - 性别: {char_a.gender.value}
  - 角色类型: {char_a.role_type.value}
  - 描述: {char_a.description or '未知'}

角色 B: {char_b.name}
  - 性别: {char_b.gender.value}
  - 角色类型: {char_b.role_type.value}
  - 描述: {char_b.description or '未知'}

对话内容（角色 A 提及角色 B）:
{text}

请分析以下内容并以 JSON 格式返回:
1. relationship_type: 关系类型，可选值: family, friend, enemy, colleague, romantic, mentor, subordinate, acquaintance, other
2. confidence: 置信度 (0.0-1.0)
3. description: 简短描述（1-2句话）

返回格式:
{{
  "relationship_type": "关系类型",
  "confidence": 0.85,
  "description": "简短描述"
}}
"""

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """
        调用 LLM API

        Args:
            prompt: 提示文本

        Returns:
            LLM 响应或 None
        """
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.llm_endpoint,
                    json={
                        "model": self.llm_model,
                        "prompt": prompt,
                        "max_tokens": 500,
                        "temperature": 0.3
                    },
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", data.get("text", ""))
                    else:
                        logger.warning(f"LLM API returned status {response.status}")

        except Exception as e:
            logger.warning(f"Failed to call LLM: {e}")

        return None

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        解析 LLM 响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的字典或 None
        """
        try:
            # 尝试提取 JSON
            # 查找 JSON 块
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)

            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)

            # 如果找不到 JSON，尝试解析整个响应
            return json.loads(response)

        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")

        return None

    def build_relationship_graph(
        self,
        relationships: List[CharacterRelationship]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        构建关系图

        Args:
            relationships: 关系列表

        Returns:
            关系图: {character_id: [关系列表]}
        """
        graph: Dict[str, List[Dict[str, Any]]] = {}

        for rel in relationships:
            # 添加 from -> to 的边
            if rel.from_character_id not in graph:
                graph[rel.from_character_id] = []

            graph[rel.from_character_id].append({
                "to": rel.to_character_id,
                "type": rel.relationship_type,
                "confidence": rel.confidence,
                "description": rel.description
            })

            # 添加 to -> from 的边（对称关系）
            if rel.to_character_id not in graph:
                graph[rel.to_character_id] = []

            graph[rel.to_character_id].append({
                "to": rel.from_character_id,
                "type": rel.relationship_type,
                "confidence": rel.confidence,
                "description": rel.description
            })

        logger.info(f"Built relationship graph with {len(graph)} nodes")

        return graph
