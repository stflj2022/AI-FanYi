"""
字幕模块清单生成器
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class DialogueManifestBuilder:
    """对话清单生成器"""

    def __init__(self, project_id: str, episode_id: str):
        """
        初始化清单生成器

        Args:
            project_id: 项目ID
            episode_id: 剧集ID
        """
        self.project_id = project_id
        self.episode_id = episode_id

    def build(
        self,
        subtitle_sources: List[Dict[str, Any]],
        dialogues: List[Dict[str, Any]],
        validation_report: Optional[Dict[str, Any]] = None,
        alignment_result: Optional[Dict[str, Any]] = None,
        statistics: Optional[Dict[str, Any]] = None,
        translation_mode: str = "existing_chinese",
        steps: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        构建对话清单

        Args:
            subtitle_sources: 字幕来源列表
            dialogues: 对话列表
            validation_report: 验证报告
            alignment_result: 对齐结果
            statistics: 统计信息
            translation_mode: 翻译模式
            steps: 执行步骤

        Returns:
            清单字典
        """
        manifest = {
            "schema_version": "1.0",
            "project_id": self.project_id,
            "episode_id": self.episode_id,
            "generated_at": datetime.utcnow().isoformat(),
            "module": "subtitle",
            "module_version": "1.0.0",

            # 执行步骤
            "steps": steps or [],

            # 字幕来源
            "subtitle_sources": subtitle_sources,

            # 翻译模式
            "translation_mode": translation_mode,

            # 验证
            "validation": validation_report or {},

            # 对齐
            "alignment": alignment_result or {},

            # 统计
            "statistics": statistics or {},

            # 对话数量
            "dialogue_count": len(dialogues),

            # 翻译状态
            "translation": {
                "source_language": "en",
                "target_language": "zh-CN",
                "method": translation_mode,
                "translated_count": sum(1 for d in dialogues if d.get('translated_text')),
                "untranslated_count": sum(1 for d in dialogues if not d.get('translated_text'))
            }
        }

        return manifest

    def save(self, manifest: Dict[str, Any], output_path: Path) -> None:
        """
        保存清单到文件

        Args:
            manifest: 清单字典
            output_path: 输出文件路径
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved dialogue manifest to {output_path}")

    def load(self, manifest_path: Path) -> Dict[str, Any]:
        """
        从文件加载清单

        Args:
            manifest_path: 清单文件路径

        Returns:
            清单字典
        """
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        logger.info(f"Loaded dialogue manifest from {manifest_path}")
        return manifest

    def create_step_result(
        self,
        step_name: str,
        status: str,
        duration: float,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建步骤结果

        Args:
            step_name: 步骤名称
            status: 状态 (success, failed, skipped)
            duration: 持续时间（秒）
            details: 详细信息

        Returns:
            步骤结果字典
        """
        return {
            "step": step_name,
            "status": status,
            "duration": duration,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
