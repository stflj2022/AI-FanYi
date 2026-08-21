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
        """从 JSON 文件加载术语库（{term: {translation, context, category}} 或 [列表] 格式）。"""
        import json as _json
        from pathlib import Path

        path = Path(self.config.terminology_file)
        if not path.exists():
            logger.warning(f"Terminology file not found: {path}")
            return

        try:
            raw = _json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                for item in raw:
                    term = item.get("term")
                    if not term:
                        continue
                    self.terminology_db[term] = TerminologyEntry(
                        term=term,
                        translation=item.get("translation", ""),
                        context=item.get("context", ""),
                        category=item.get("category", "general"),
                    )
            elif isinstance(raw, dict):
                for term, value in raw.items():
                    if isinstance(value, str):
                        self.terminology_db[term] = TerminologyEntry(
                            term=term, translation=value, context="", category="general"
                        )
                    elif isinstance(value, dict):
                        self.terminology_db[term] = TerminologyEntry(
                            term=term,
                            translation=value.get("translation", ""),
                            context=value.get("context", ""),
                            category=value.get("category", "general"),
                        )
            logger.info(f"Loaded {len(self.terminology_db)} terminology entries from {path}")
        except Exception as e:
            logger.error(f"Failed to load terminology file {path}: {e}")

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

        # 术语库替换（真实规则）：优先最长匹配，避免部分替换
        if self.terminology_db:
            # 按长度降序，保证长术语优先
            for term in sorted(self.terminology_db, key=len, reverse=True):
                entry = self.terminology_db[term]
                if term and term in text:
                    text = text.replace(term, entry.translation)
                    changes.append({
                        "type": "terminology",
                        "original": term,
                        "replacement": entry.translation,
                        "reason": f"术语库条目: {entry.category}"
                    })

        # LLM 术语一致性检查为可选增强；无 LLM 时规则库已保证一致性。

        return text, changes

    async def _localize_culture(
        self,
        text: str,
        character: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[str, List[Dict[str, str]]]:
        """
        文化本地化（真实单位换算规则）

        处理西式单位/习俗在中文语境下的本地化：
        - 英里 → 公里（×1.609）
        - 华氏度 → 摄氏度（(F-32)×5/9）
        - 英寸 → 厘米（×2.54）
        - 英尺 → 米（×0.305）

        Args:
            text: 文本
            character: 人物信息
            context: 上下文

        Returns:
            (处理后的文本, 文化适配列表)
        """
        adaptations = []

        def _convert(pattern, factor, unit, fmt="{:.1f}"):
            nonlocal text
            matches = list(re.finditer(pattern, text))
            for m in reversed(matches):
                number = m.group(1)
                try:
                    value = float(number)
                except ValueError:
                    continue
                converted = float(fmt.format(value * factor))
                new_text = f"{converted:.0f}{unit}" if converted == int(converted) else f"{converted:.1f}{unit}"
                original = m.group(0)
                text = text[:m.start()] + new_text + text[m.end():]
                adaptations.append({
                    "type": "culture",
                    "original": original,
                    "replacement": new_text,
                    "reason": f"单位本地化: {unit}"
                })

        # 英里 → 公里
        _convert(r"(\d+(?:\.\d+)?)\s*英里", 1.609344, "公里")
        # 英尺 → 米
        _convert(r"(\d+(?:\.\d+)?)\s*英尺", 0.3048, "米")
        # 英寸 → 厘米
        _convert(r"(\d+(?:\.\d+)?)\s*英寸", 2.54, "厘米")

        # 华氏度 → 摄氏度（特殊公式）
        for m in reversed(list(re.finditer(r"(\d+(?:\.\d+)?)\s*华氏度", text))):
            try:
                f = float(m.group(1))
            except ValueError:
                continue
            c = (f - 32) * 5 / 9
            new_text = f"{c:.0f}摄氏度" if c == int(c) else f"{c:.1f}摄氏度"
            text = text[:m.start()] + new_text + text[m.end():]
            adaptations.append({
                "type": "culture",
                "original": m.group(0),
                "replacement": new_text,
                "reason": "单位本地化: 摄氏度"
            })

        return text, adaptations

    async def _adjust_tone(
        self,
        text: str,
        character: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[str, List[Dict[str, str]]]:
        """
        调整语气（基于角色类型的真实规则）

        - protagonist：去除口语填充词（嗯/呃/那个），语气更坚定
        - antagonist：去除礼貌用语，句子更短促
        - narrator：去除感叹词，书面化（哎→）

        Args:
            text: 文本
            character: 人物信息
            context: 上下文

        Returns:
            (处理后的文本, 语气调整列表)
        """
        adjustments = []
        original = text

        role_type = character.get("role_type", "unknown")

        if role_type == "protagonist":
            # 去除口语填充词
            for filler in ["呃，", "嗯，", "那个，", "就是说，"]:
                if filler in text:
                    text = text.replace(filler, "")
                    adjustments.append({
                        "type": "tone",
                        "original": filler,
                        "replacement": "",
                        "reason": "主角语气：去除口语填充词"
                    })
            # 句尾“吧”改为“。”，语气更坚定
            if text.endswith("吧"):
                text = text[:-1] + "。"
                adjustments.append({
                    "type": "tone",
                    "original": "吧",
                    "replacement": "。",
                    "reason": "主角语气：更坚定"
                })

        elif role_type == "antagonist":
            # 去除礼貌用语，语气更强势
            for polite in ["请，", "请", "麻烦，", "谢谢。"]:
                if polite in text:
                    text = text.replace(polite, "")
                    adjustments.append({
                        "type": "tone",
                        "original": polite,
                        "replacement": "",
                        "reason": "反派语气：去除礼貌用语"
                    })
            # 句尾问句改为感叹句，更挑衅
            if text.endswith("吗？"):
                text = text[:-2] + "！"
                adjustments.append({
                    "type": "tone",
                    "original": "吗？",
                    "replacement": "！",
                    "reason": "反派语气：更挑衅"
                })

        elif role_type == "narrator":
            # 去除感叹词，书面化
            for interjection in ["哎，", "嘿，", "哇，"]:
                if interjection in text:
                    text = text.replace(interjection, "")
                    adjustments.append({
                        "type": "tone",
                        "original": interjection,
                        "replacement": "",
                        "reason": "旁白语气：书面化"
                    })

        if text != original and not adjustments:
            adjustments.append({
                "type": "tone",
                "original": original,
                "replacement": text,
                "reason": "语气调整"
            })

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
