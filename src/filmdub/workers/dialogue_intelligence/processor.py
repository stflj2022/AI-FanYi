"""
对白智能处理器

处理对白翻译，包括术语检查、文化本地化和语气调整
"""
from typing import List, Dict, Any, Optional
from loguru import logger
import re

from .config import M07Config


class DialogueIntelligence:
    """对白智能处理器"""

    def __init__(self, config: M07Config = None):
        """
        初始化处理器

        Args:
            config: M07 配置
        """
        self.config = config or M07Config()

        # 加载术语库
        self.terminology_db = {}
        if self.config.terminology_db_path:
            self._load_terminology_db()

    def process_dialogue(
        self,
        dialogues: List[Dict[str, Any]],
        characters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        处理对白

        Args:
            dialogues: 对白列表
                [{"character_id": str, "text": str, "start_time": float, ...}]
            characters: 人物列表

        Returns:
            处理后的对白列表
        """
        logger.info(f"Processing {len(dialogues)} dialogues")

        processed_dialogues = []

        for i, dialogue in enumerate(dialogues):
            try:
                # 获取人物信息
                character = self._get_character(
                    dialogue.get("character_id"),
                    characters
                )

                # 1. 术语检查
                if self.config.enable_terminology_check:
                    dialogue = self._check_terminology(dialogue)

                # 2. 文化本地化
                if self.config.enable_culture_localization:
                    dialogue = self._localize_culture(dialogue, character)

                # 3. 语气调整
                if self.config.enable_tone_adjustment:
                    dialogue = self._adjust_tone(dialogue, character)

                processed_dialogues.append(dialogue)

            except Exception as e:
                logger.warning(f"Failed to process dialogue {i}: {e}")
                # 保留原始对白
                processed_dialogues.append(dialogue)

        logger.info(f"Processed {len(processed_dialogues)} dialogues")

        return processed_dialogues

    def _get_character(
        self,
        character_id: str,
        characters: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """获取人物信息"""
        for character in characters:
            if character.get("character_id") == character_id:
                return character
        return None

    def _check_terminology(self, dialogue: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查术语一致性

        Args:
            dialogue: 对白

        Returns:
            更新后的对白
        """
        text = dialogue.get("text", "")
        warnings = []

        # 检查术语库
        for term, translation in self.terminology_db.items():
            if term.lower() in text.lower():
                # 检查是否使用了正确的翻译
                if translation not in text:
                    warnings.append({
                        "type": "terminology",
                        "term": term,
                        "expected_translation": translation,
                        "message": f"术语 '{term}' 应翻译为 '{translation}'"
                    })

        # 添加警告
        if warnings:
            if "warnings" not in dialogue:
                dialogue["warnings"] = []
            dialogue["warnings"].extend(warnings)

        return dialogue

    def _localize_culture(
        self,
        dialogue: Dict[str, Any],
        character: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        文化本地化

        Args:
            dialogue: 对白
            character: 人物信息

        Returns:
            更新后的对白
        """
        text = dialogue.get("text", "")

        # 简化版：使用 LLM 进行文化本地化
        # 实际实现应该调用本地 LLM

        # TODO: 调用 LLM 进行文化本地化
        # 这里只是框架

        return dialogue

    def _adjust_tone(
        self,
        dialogue: Dict[str, Any],
        character: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        调整语气

        Args:
            dialogue: 对白
            character: 人物信息

        Returns:
            更新后的对白
        """
        text = dialogue.get("text", "")

        # 根据人物角色类型调整语气
        role_type = character.get("role_type", "unknown") if character else "unknown"

        # 简化版：使用 LLM 进行语气调整
        # 实际实现应该调用本地 LLM

        # TODO: 调用 LLM 进行语气调整
        # 这里只是框架

        return dialogue

    def _load_terminology_db(self):
        """加载术语库"""
        try:
            # TODO: 从文件加载术语库
            # 这里只是框架
            logger.info("Terminology DB loaded")
        except Exception as e:
            logger.warning(f"Failed to load terminology DB: {e}")

    async def call_llm(self, prompt: str) -> str:
        """
        调用 LLM

        Args:
            prompt: 提示词

        Returns:
            LLM 响应
        """
        # TODO: 实际调用 LLM
        # 这里只是框架
        return ""
