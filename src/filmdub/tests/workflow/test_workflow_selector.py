"""WorkflowSelector 单元测试"""

import pytest
from filmdub.orchestrator.workflow.workflow_selector import (
    WorkflowType,
    SelectionReason,
    WorkflowSelector,
)
from filmdub.orchestrator.workflow.task_context import (
    TaskContext,
    TaskType,
    QualityRequirement,
    SubtitleStatus,
    AudioStatus,
    DatabaseStatus,
)
from filmdub.orchestrator.workflow.capability_matrix import (
    CapabilityMatrix,
    CapabilityEntry,
    CapabilityState,
)


def _create_basic_context(
    task_type: TaskType = TaskType.EPISODE,
    quality_requirement: QualityRequirement = QualityRequirement.STANDARD,
    force_workflow: str = None,
    duration_seconds: float = 45 * 60,
    subtitle: SubtitleStatus = None,
) -> TaskContext:
    """创建基础任务上下文"""
    if subtitle is None:
        subtitle = SubtitleStatus(exists=False)

    return TaskContext(
        project_id="test_project",
        media_id="S01E01",
        task_type=task_type,
        quality_requirement=quality_requirement,
        force_workflow=force_workflow,
        duration_seconds=duration_seconds,
        subtitle=subtitle,
        audio=AudioStatus(exists=False),
        character_db=DatabaseStatus(exists=False),
        voice_db=DatabaseStatus(exists=False),
        story_db=DatabaseStatus(exists=False),
        translation_memory=DatabaseStatus(exists=False),
    )


def _create_basic_matrix(
    video_state: CapabilityState = CapabilityState.NONE,
    audio_state: CapabilityState = CapabilityState.NONE,
    character_db_state: CapabilityState = CapabilityState.NONE,
    voice_db_state: CapabilityState = CapabilityState.NONE,
) -> CapabilityMatrix:
    """创建基础能力矩阵"""
    return CapabilityMatrix(
        video=CapabilityEntry(state=video_state),
        audio=CapabilityEntry(state=audio_state),
        subtitle=CapabilityEntry(state=CapabilityState.NONE),
        character_db=CapabilityEntry(state=character_db_state),
        voice_db=CapabilityEntry(state=voice_db_state),
        story_db=CapabilityEntry(state=CapabilityState.NONE),
        translation_memory=CapabilityEntry(state=CapabilityState.NONE),
    )


class TestWorkflowType:
    """WorkflowType 测试"""

    def test_enum_values(self):
        """测试枚举值"""
        assert WorkflowType.QUICK.value == "quick"
        assert WorkflowType.STANDARD.value == "standard"
        assert WorkflowType.PRODUCTION.value == "production"
        assert WorkflowType.PREVIEW.value == "preview"
        assert WorkflowType.REVOICE.value == "revoice"
        assert WorkflowType.RERENDER.value == "rerender"
        assert WorkflowType.QA_ONLY.value == "qa_only"


class TestSelectionReason:
    """SelectionReason 测试"""

    def test_create_basic(self):
        """测试创建基本选择原因"""
        reason = SelectionReason(
            workflow_type=WorkflowType.QUICK,
            reason="快速处理",
        )
        assert reason.workflow_type == WorkflowType.QUICK
        assert reason.reason == "快速处理"
        assert reason.confidence == 1.0

    def test_create_with_details(self):
        """测试创建带详细信息的选择原因"""
        reason = SelectionReason(
            workflow_type=WorkflowType.STANDARD,
            reason="标准处理",
            confidence=0.9,
            factors={"video_length": "short", "subtitle": "verified"},
        )
        assert reason.confidence == 0.9
        assert reason.factors["video_length"] == "short"


class TestWorkflowSelector:
    """WorkflowSelector 测试"""

    def test_init(self):
        """测试初始化"""
        selector = WorkflowSelector()
        assert selector.rules is not None
        assert len(selector.rules) > 0

    def test_rule_user_requirement_quick(self):
        """测试规则：用户要求快速"""
        context = _create_basic_context(
            quality_requirement=QualityRequirement.QUICK,
        )
        matrix = _create_basic_matrix()

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.workflow_type == WorkflowType.QUICK
        assert "用户要求" in result.reason

    def test_rule_user_requirement_production(self):
        """测试规则：用户要求生产级"""
        context = _create_basic_context(
            quality_requirement=QualityRequirement.PRODUCTION,
        )
        matrix = _create_basic_matrix()

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.workflow_type == WorkflowType.PRODUCTION
        assert "生产级" in result.reason

    def test_force_workflow(self):
        """测试强制工作流"""
        context = _create_basic_context(
            force_workflow="quick",
        )
        matrix = _create_basic_matrix()

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.workflow_type == WorkflowType.QUICK
        assert "强制" in result.reason

    def test_rule_task_type_qa(self):
        """测试规则：QA 任务"""
        context = _create_basic_context(
            task_type=TaskType.QA,
        )
        matrix = _create_basic_matrix()

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.workflow_type == WorkflowType.QA_ONLY
        assert "质检" in result.reason

    def test_rule_task_type_rerender(self):
        """测试规则：重新渲染任务"""
        context = _create_basic_context(
            task_type=TaskType.RERENDER,
        )
        matrix = _create_basic_matrix()

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.workflow_type == WorkflowType.RERENDER
        assert "重新渲染" in result.reason

    def test_rule_task_type_revoice(self):
        """测试规则：重新配音任务"""
        context = _create_basic_context(
            task_type=TaskType.REVOICE,
        )
        matrix = _create_basic_matrix()

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.workflow_type == WorkflowType.REVOICE
        assert "重新配音" in result.reason

    def test_rule_task_type_preview(self):
        """测试规则：预览任务"""
        context = _create_basic_context(
            task_type=TaskType.PREVIEW,
        )
        matrix = _create_basic_matrix()

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.workflow_type == WorkflowType.PREVIEW
        assert "预览" in result.reason

    def test_rule_full_assets_quick(self):
        """测试规则：已有全部资产 + 快速任务"""
        context = _create_basic_context(
            task_type=TaskType.CLIP,  # 使用 CLIP 而不是 PREVIEW
        )
        matrix = _create_basic_matrix(
            video_state=CapabilityState.COMPLETE,
            audio_state=CapabilityState.COMPLETE,
            character_db_state=CapabilityState.COMPLETE,
            voice_db_state=CapabilityState.COMPLETE,
        )

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.workflow_type == WorkflowType.QUICK
        assert "完整资产" in result.reason

    def test_rule_production_ready(self):
        """测试规则：准备好生产级处理"""
        context = _create_basic_context(
            task_type=TaskType.MOVIE,
            duration_seconds=120 * 60,  # 2小时
        )
        matrix = _create_basic_matrix(
            video_state=CapabilityState.COMPLETE,
            audio_state=CapabilityState.COMPLETE,
            character_db_state=CapabilityState.COMPLETE,
            voice_db_state=CapabilityState.COMPLETE,
        )

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.workflow_type == WorkflowType.PRODUCTION
        assert "生产级" in result.reason

    def test_rule_standard_ready(self):
        """测试规则：准备好标准处理"""
        context = _create_basic_context(
            task_type=TaskType.EPISODE,
        )
        matrix = _create_basic_matrix(
            video_state=CapabilityState.COMPLETE,
            audio_state=CapabilityState.PARTIAL,
            character_db_state=CapabilityState.PARTIAL,
            voice_db_state=CapabilityState.PARTIAL,
        )

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.workflow_type == WorkflowType.STANDARD
        assert "标准" in result.reason

    def test_rule_no_subtitle_quick(self):
        """测试规则：无字幕使用快速工作流"""
        context = _create_basic_context(
            subtitle=SubtitleStatus(exists=False),
        )
        matrix = _create_basic_matrix()

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.workflow_type == WorkflowType.QUICK
        assert "无字幕" in result.reason

    def test_rule_short_video_quick(self):
        """测试规则：短视频使用快速工作流"""
        context = _create_basic_context(
            duration_seconds=15 * 60,  # 15分钟
            subtitle=SubtitleStatus(exists=True, quality="unknown"),
        )
        matrix = _create_basic_matrix()

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.workflow_type == WorkflowType.QUICK
        assert "短视频" in result.reason

    def test_rule_short_video_with_verified_subtitle(self):
        """测试规则：短视频 + 已验证字幕使用标准工作流"""
        context = _create_basic_context(
            duration_seconds=15 * 60,  # 15分钟
            subtitle=SubtitleStatus(exists=True, quality="verified"),
        )
        matrix = _create_basic_matrix()

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.workflow_type == WorkflowType.STANDARD
        assert "已验证字幕" in result.reason

    def test_rule_long_video_production(self):
        """测试规则：长视频优先生产级处理"""
        context = _create_basic_context(
            task_type=TaskType.EPISODE,
            duration_seconds=60 * 60,  # 1小时
            subtitle=SubtitleStatus(exists=True, quality="verified"),  # 有字幕
        )
        matrix = _create_basic_matrix(
            video_state=CapabilityState.COMPLETE,
            audio_state=CapabilityState.COMPLETE,
        )

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.workflow_type == WorkflowType.PRODUCTION
        assert "长视频" in result.reason

    def test_default_fallback(self):
        """测试默认回退到 STANDARD"""
        context = _create_basic_context(
            duration_seconds=30 * 60,  # 30分钟
            subtitle=SubtitleStatus(exists=True, quality="verified"),  # 有字幕
        )
        matrix = _create_basic_matrix(
            video_state=CapabilityState.COMPLETE,
            audio_state=CapabilityState.COMPLETE,
        )

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        # 有字幕的中等长度视频，应该选择 STANDARD 或 PRODUCTION
        assert result.workflow_type in [WorkflowType.STANDARD, WorkflowType.PRODUCTION]

    def test_confidence_values(self):
        """测试信心度值"""
        # 强制工作流信心度为 1.0
        context = _create_basic_context(force_workflow="quick")
        matrix = _create_basic_matrix()

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert result.confidence == 1.0

    def test_factors(self):
        """测试决策因素"""
        context = _create_basic_context(quality_requirement=QualityRequirement.QUICK)
        matrix = _create_basic_matrix()

        selector = WorkflowSelector()
        result = selector.select(context, matrix)

        assert "quality_requirement" in result.factors
        assert result.factors["quality_requirement"] == "quick"
