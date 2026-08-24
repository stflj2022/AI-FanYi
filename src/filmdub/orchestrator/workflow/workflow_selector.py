"""Workflow Selector - 工作流选择器

基于规则引擎 + 打分 + 硬约束，根据 TaskContext + CapabilityMatrix
选择工作流类型（QUICK/STANDARD/PRODUCTION 等）。

决策优先级：
1. 用户明确要求
2. 任务类型
3. 已有资产
4. 资产质量
5. 字幕状态
6. 视频长度
"""

from enum import Enum
from typing import Optional, Dict, List, Tuple
from pydantic import BaseModel, Field

from .task_context import TaskContext, TaskType, QualityRequirement
from .capability_matrix import CapabilityMatrix, CapabilityState


class WorkflowType(str, Enum):
    """工作流类型"""
    QUICK = "quick"  # 快速
    STANDARD = "standard"  # 标准
    PRODUCTION = "production"  # 生产
    PREVIEW = "preview"  # 预览
    REVOICE = "revoice"  # 重新配音
    RERENDER = "rerender"  # 重新渲染
    QA_ONLY = "qa_only"  # 仅质检


class SelectionReason(BaseModel):
    """选择原因"""
    workflow_type: WorkflowType
    reason: str
    confidence: float = 1.0  # 信心度 0.0-1.0
    factors: Dict[str, str] = Field(default_factory=dict)


class WorkflowSelector:
    """工作流选择器

    基于规则引擎选择工作流类型。
    """

    def __init__(self):
        """初始化选择器"""
        self.rules = self._build_rules()

    def select(
        self,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> SelectionReason:
        """选择工作流

        Args:
            task_context: 任务上下文
            capability_matrix: 能力矩阵

        Returns:
            SelectionReason 选择结果
        """
        # 1. 检查用户强制指定
        if task_context.force_workflow:
            workflow = self._parse_force_workflow(task_context.force_workflow)
            return SelectionReason(
                workflow_type=workflow,
                reason=f"用户强制指定工作流: {task_context.force_workflow}",
                confidence=1.0,
                factors={"force": task_context.force_workflow},
            )

        # 2. 按照规则引擎决策
        for rule_name, rule_func in self.rules.items():
            result = rule_func(task_context, capability_matrix)
            if result is not None:
                return result

        # 3. 默认返回 STANDARD
        return SelectionReason(
            workflow_type=WorkflowType.STANDARD,
            reason="默认选择标准工作流",
            confidence=0.5,
            factors={"default": "true"},
        )

    def _build_rules(self) -> Dict[str, callable]:
        """构建规则集

        Returns:
            规则字典，按优先级顺序
        """
        return {
            # 用户明确要求（通过 quality_requirement）
            "user_requirement": self._rule_user_requirement,

            # 任务类型驱动
            "task_type_qa": self._rule_task_type_qa,
            "task_type_rerender": self._rule_task_type_rerender,
            "task_type_revoice": self._rule_task_type_revoice,
            "task_type_preview": self._rule_task_type_preview,

            # 已有资产 + 任务类型
            "full_assets_quick": self._rule_full_assets_quick,
            "full_assets_preview": self._rule_full_assets_preview,

            # 资产质量驱动
            "production_ready": self._rule_production_ready,
            "standard_ready": self._rule_standard_ready,

            # 字幕状态
            "no_subtitle_quick": self._rule_no_subtitle_quick,

            # 视频长度
            "short_video_quick": self._rule_short_video_quick,
            "long_video_production": self._rule_long_video_production,
        }

    def _parse_force_workflow(self, force_workflow: str) -> WorkflowType:
        """解析强制工作流类型"""
        force_lower = force_workflow.lower()
        for workflow_type in WorkflowType:
            if workflow_type.value == force_lower:
                return workflow_type
        # 默认返回 STANDARD
        return WorkflowType.STANDARD

    # ===== 规则实现 =====

    def _rule_user_requirement(
        self,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> Optional[SelectionReason]:
        """规则：用户明确要求"""
        if task_context.quality_requirement == QualityRequirement.QUICK:
            return SelectionReason(
                workflow_type=WorkflowType.QUICK,
                reason="用户要求快速处理",
                confidence=1.0,
                factors={"quality_requirement": "quick"},
            )
        elif task_context.quality_requirement == QualityRequirement.PRODUCTION:
            return SelectionReason(
                workflow_type=WorkflowType.PRODUCTION,
                reason="用户要求生产级质量",
                confidence=1.0,
                factors={"quality_requirement": "production"},
            )
        return None

    def _rule_task_type_qa(
        self,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> Optional[SelectionReason]:
        """规则：QA 任务"""
        if task_context.task_type == TaskType.QA:
            return SelectionReason(
                workflow_type=WorkflowType.QA_ONLY,
                reason="质检任务",
                confidence=1.0,
                factors={"task_type": "qa"},
            )
        return None

    def _rule_task_type_rerender(
        self,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> Optional[SelectionReason]:
        """规则：重新渲染任务"""
        if task_context.task_type == TaskType.RERENDER:
            return SelectionReason(
                workflow_type=WorkflowType.RERENDER,
                reason="重新渲染任务",
                confidence=1.0,
                factors={"task_type": "rerender"},
            )
        return None

    def _rule_task_type_revoice(
        self,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> Optional[SelectionReason]:
        """规则：重新配音任务"""
        if task_context.task_type == TaskType.REVOICE:
            return SelectionReason(
                workflow_type=WorkflowType.REVOICE,
                reason="重新配音任务",
                confidence=1.0,
                factors={"task_type": "revoice"},
            )
        return None

    def _rule_task_type_preview(
        self,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> Optional[SelectionReason]:
        """规则：预览任务"""
        if task_context.task_type == TaskType.PREVIEW:
            return SelectionReason(
                workflow_type=WorkflowType.PREVIEW,
                reason="预览任务",
                confidence=1.0,
                factors={"task_type": "preview"},
            )
        return None

    def _rule_full_assets_quick(
        self,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> Optional[SelectionReason]:
        """规则：已有全部资产 + 快速任务"""
        # 检查是否已有完整资产
        has_full_assets = (
            capability_matrix.is_ready_for_production()
            or capability_matrix.is_ready_for_standard()
        )

        # 快速任务类型
        is_quick_task = task_context.task_type in [
            TaskType.PREVIEW,
            TaskType.CLIP,
        ]

        if has_full_assets and is_quick_task:
            return SelectionReason(
                workflow_type=WorkflowType.QUICK,
                reason="已有完整资产，快速任务",
                confidence=0.9,
                factors={
                    "full_assets": "true",
                    "task_type": task_context.task_type.value,
                },
            )
        return None

    def _rule_full_assets_preview(
        self,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> Optional[SelectionReason]:
        """规则：已有全部资产 + 试听/模型测试"""
        has_full_assets = capability_matrix.is_ready_for_production()

        if has_full_assets and task_context.task_type == TaskType.EPISODE:
            return SelectionReason(
                workflow_type=WorkflowType.PREVIEW,
                reason="已有完整资产，用于试听或模型测试",
                confidence=0.8,
                factors={"full_assets": "true"},
            )
        return None

    def _rule_production_ready(
        self,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> Optional[SelectionReason]:
        """规则：准备好生产级处理"""
        if capability_matrix.is_ready_for_production():
            # 长视频或完整项目
            if (
                not task_context.is_short_video()
                or task_context.task_type in [TaskType.MOVIE, TaskType.SEASON]
            ):
                return SelectionReason(
                    workflow_type=WorkflowType.PRODUCTION,
                    reason="资产完整，适合生产级处理",
                    confidence=0.95,
                    factors={
                        "ready_for_production": "true",
                        "video_length": "long" if not task_context.is_short_video() else "short",
                    },
                )
        return None

    def _rule_standard_ready(
        self,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> Optional[SelectionReason]:
        """规则：准备好标准处理"""
        if capability_matrix.is_ready_for_standard():
            # 单集或普通电影
            if task_context.task_type in [TaskType.EPISODE, TaskType.MOVIE]:
                return SelectionReason(
                    workflow_type=WorkflowType.STANDARD,
                    reason="资产满足标准处理要求",
                    confidence=0.9,
                    factors={"ready_for_standard": "true"},
                )
        return None

    def _rule_no_subtitle_quick(
        self,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> Optional[SelectionReason]:
        """规则：无字幕使用快速工作流"""
        if not task_context.has_subtitle():
            return SelectionReason(
                workflow_type=WorkflowType.QUICK,
                reason="无字幕，使用快速工作流",
                confidence=0.7,
                factors={"subtitle": "none"},
            )
        return None

    def _rule_short_video_quick(
        self,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> Optional[SelectionReason]:
        """规则：短视频使用快速工作流"""
        if task_context.is_short_video():
            # 如果已有字幕，可以考虑标准流程
            if task_context.has_verified_subtitle():
                return SelectionReason(
                    workflow_type=WorkflowType.STANDARD,
                    reason="短视频 + 已验证字幕，使用标准工作流",
                    confidence=0.85,
                    factors={"video_length": "short", "subtitle": "verified"},
                )
            else:
                return SelectionReason(
                    workflow_type=WorkflowType.QUICK,
                    reason="短视频，使用快速工作流",
                    confidence=0.8,
                    factors={"video_length": "short"},
                )
        return None

    def _rule_long_video_production(
        self,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> Optional[SelectionReason]:
        """规则：长视频优先生产级处理"""
        if not task_context.is_short_video():
            # 长视频 + 完整任务类型
            if task_context.task_type in [TaskType.MOVIE, TaskType.SEASON, TaskType.EPISODE]:
                return SelectionReason(
                    workflow_type=WorkflowType.PRODUCTION,
                    reason="长视频，使用生产级工作流",
                    confidence=0.75,
                    factors={"video_length": "long"},
                )
        return None
