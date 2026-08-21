"""
对白智能处理器

使用 LLM 进行对白智能处理，包括术语一致性检查、文化本地化和语气调整
"""
import json
import re
from typing import List, Optional, Dict, Any, Set
import logging

logger = logging.getLogger(__name__)

from .models import ProcessedDialogue, TerminologyEntry
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
        self.terminology_db: Dict[str, TerminologyEntry] = {}

        # 加载术语库
        if self.config.enable_terminology_check and self.config.terminology_file:
            self._load_terminology()

    def _load_terminology(self):
        """加载术语库"""
        # TODO: 从文件加载术语库
        pass

    async def process_dialogues(
        self,
        dialogues: List[Dict[str, Any]],
        characters: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[ProcessedDialogue]:
        """
        处理对白列表

        Args:
            dialogues: 对白列表
            characters: 人物列表
            context: 上下文信息

        Returns:
            处理后的对白列表
        """
        logger.info(f"Processing {len(dialogues)} dialogues")

        processed_dialogues = []

        for dialogue in dialogues:
            processed = await self.process_dialogue(
                dialogue,
                characters,
                context
            )

            if processed:
                processed_dialogues.append(processed)

        logger.info(f"Processed {len(processed_dialogues)} dialogues successfully")

        return processed_dialogues

    async def process_dialogue(
        self,
        dialogue: Dict[str, Any],
        characters: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ProcessedDialogue]:
        """
        处理单个对白

        Args:
            dialogue: 对白数据
            characters: 人物列表
            context: 上下文信息

        Returns:
            处理后的对白或 None
        """
        original_text = dialogue.get("text", "")
        character_id = dialogue.get("character_id")
        speaker_id = dialogue.get("speaker_id")

        if not original_text:
            return None

        # 查找人物信息
        character = next(
            (c for c in characters if c["character_id"] == character_id),
            None
        )

        if not character:
            logger.warning(f"Character {character_id} not found")
            return None

        # 初始化处理结果
        processed_text = original_text
        terminology_changes = []
        cultural_adaptations = []
        tone_adjustments = []

        # 1. 术语一致性检查
        if self.config.enable_terminology_check:
            processed_text, term_changes = await self._check_terminology(
                processed_text,
                context
            )
            terminology_changes.extend(term_changes)

        # 2. 文化本地化
        if self.config.enable_culture_localization:
            processed_text, cultural_changes = await self._localize_culture(
                processed_text,
                character,
                context
            )
            cultural_adaptations.extend(cultural_changes)

        # 3. 语气调整
        if self.config.enable_tone_adjustment:
            processed_text, tone_changes = await self._adjust_tone(
                processed_text,
                character,
                context
            )
            tone_adjustments.extend(tone_changes)

        # 计算置信度
        confidence = self._calculate_confidence(
            terminology_changes,
            cultural_adaptations,
            tone_adjustments
        )

        # 判断是否需要人工审核
        needs_review = confidence < 0.7 or len(tone_adjustments) > 3

        return ProcessedDialogue(
            dialogue_id=dialogue.get("dialogue_id", ""),
            original_text=original_text,
            processed_text=processed_text,
            character_id=character_id,
            speaker_id=speaker_id,
            start_time=dialogue.get("start_time", 0.0),
            end_time=dialogue.get("end_time", 0.0),
            terminology_changes=terminology_changes,
            cultural_adaptations=cultural_adaptations,
            tone_adjustments=tone_adjustments,
            confidence=confidence,
            needs_manual_review=needs_review
        )

    async def _check_terminology(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[str, List[Dict[str, str]]]:
        """
        检查术语一致性

        Args:
            text: 文本
            context: 上下文

        Returns:
            (处理后的文本, 术语变更列表)
        """
        changes = []

        # 如果有术语库，使用术语库
        if self.terminology_db:
            for term, entry in self.terminology_db.items():
                if term in text:
                    old_text = text
                    text = text.replace(term, entry.translation)
                    changes.append({
                        "type": "terminology",
                        "original": term,
                        "replacement": entry.translation,
                        "reason": f"术语库条目: {entry.category}"
                    })

        # TODO: 使用 LLM 检查术语一致性

        return text, changes

    async def _localize_culture(
        self,
        text: str,
        character: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[str, List[Dict[str, str]]]:
        """
        文化本地化

        Args:
            text: 文本
            character: 人物信息
            context: 上下文

        Returns:
            (处理后的文本, 文化适配列表)
        """
        adaptations = []

        # 简单规则：检测常见文化差异
        culture_patterns = [
            (r"公里", "千米", "单位本地化"),
            (r"英尺", "英尺", "保留英尺（文化特征）"),
            (r"美元", "美元", "保留货币单位"),
        ]

        for pattern, replacement, reason in culture_patterns:
            if re.search(pattern, text):
                old_text = text
                text = re.sub(pattern, replacement, text)
                if old_text != text:
                    adaptations.append({
                        "type": "culture",
                        "original": old_text,
                        "replacement": text,
                        "reason": reason
                    })

        # TODO: 使用 LLM 进行更复杂的文化本地化

        return text, adaptations

    async def _adjust_tone(
        self,
        text: str,
        character: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[str, List[Dict[str, str]]]:
        """
        调整语气

        Args:
            text: 文本
            character: 人物信息
            context: 上下文

        Returns:
            (处理后的文本, 语气调整列表)
        """
        adjustments = []

        # 基于角色类型调整语气
        role_type = character.get("role_type", "unknown")

        # 简化版：使用规则调整
        if role_type == "protagonist":
            # 主角：自信、坚定
            pass
        elif role_type == "antagonist":
            # 反派：威胁、挑衅
            pass
        elif role_type == "narrator":
            # 旁白：客观、冷静
            pass

        # TODO: 使用 LLM 进行语气调整
        prompt = self._build_tone_adjustment_prompt(text, character, context)

        # llm_result = await self._call_llm(prompt)
        # if llm_result:
        #     text, adjustments = self._parse_tone_result(llm_result)

        return text, adjustments

    def _build_tone_adjustment_prompt(
        self,
        text: str,
        character: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建语气调整提示"""
        return f"""
你是一个影视台词编辑专家。请根据角色特点调整以下台词的语气。

角色信息:
- 姓名: {character.get('name', '未知')}
- 性别: {character.get('gender', '未知')}
- 角色类型: {character.get('role_type', '未知')}
- 描述: {character.get('description', '未知')}

原台词:
{text}

请调整语气以更符合角色特点，返回 JSON 格式:
{{
  "adjusted_text": "调整后的台词",
  "changes": [
    {{
      "type": "tone",
      "original": "原文片段",
      "replacement": "修改后片段",
      "reason": "修改原因"
    }}
  ]
}}
"""

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """调用 LLM"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.llm_endpoint,
                    json={
                        "model": self.config.llm_model,
                        "prompt": prompt,
                        "max_tokens": 500,
                        "temperature": 0.3
                    },
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", data.get("text", ""))

        except Exception as e:
            logger.warning(f"Failed to call LLM: {e}")

        return None

    def _calculate_confidence(
        self,
        term_changes: List[Dict],
        cultural_adaptations: List[Dict],
        tone_adjustments: List[Dict]
    ) -> float:
        """计算置信度"""
        # 简化版：基于变更数量计算
        total_changes = len(term_changes) + len(cultural_adaptations) + len(tone_adjustments)

        # 变更越多，置信度越低
        confidence = max(0.0, 1.0 - (total_changes * 0.1))

        return confidence
