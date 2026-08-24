"""测试工作流规划器"""

import pytest

from filmdub.orchestrator.workflow.workflow_planner import (
    WorkflowPlanner,
    ExecutionPlan,
    ExecutionStep,
    ExecutionMode,
)
from filmdub.orchestrator.workflow.dependency_resolver import DependencyResolver
from filmdub.orchestrator.workflow.task_context import (
    TaskContext,
    TaskType,
    SubtitleStatus,
    AudioStatus,
    DatabaseStatus,
    QualityRequirement,
)
from filmdub.orchestrator.workflow.capability_matrix import (
    CapabilityMatrix,
    CapabilityState,
    CapabilityEntry,
)
from filmdub.orchestrator.workflow.workflow_selector import WorkflowType


class TestExecutionStep:
    """测试执行步骤"""

    def test_create_step(self):
        """测试创建执行步骤"""
        step = ExecutionStep(
            module="M09",
            mode=ExecutionMode.RUN_FULL,
            dependencies=["M08", "M04"],
            reason="声音库不存在，完整合成"
        )
        assert step.module == "M09"
        assert step.mode == ExecutionMode.RUN_FULL
        assert "M08" in step.dependencies
        assert "M04" in step.dependencies


class TestExecutionPlan:
    """测试执行计划"""

    def test_create_plan(self):
        """测试创建执行计划"""
        plan = ExecutionPlan(
            plan_id="plan_12345678",
            workflow_type=WorkflowType.STANDARD,
            steps=[
                ExecutionStep(module="M04", mode=ExecutionMode.RUN_FULL),
                ExecutionStep(module="M09", mode=ExecutionMode.RUN_FULL, dependencies=["M04"]),
            ]
        )
        assert plan.plan_id == "plan_12345678"
        assert plan.workflow_type == WorkflowType.STANDARD
        assert len(plan.steps) == 2

    def test_get_steps_by_module(self):
        """测试按模块获取步骤"""
        plan = ExecutionPlan(
            plan_id="plan_12345678",
            workflow_type=WorkflowType.STANDARD,
            steps=[
                ExecutionStep(module="M04", mode=ExecutionMode.RUN_FULL),
                ExecutionStep(module="M09", mode=ExecutionMode.RUN_FULL, dependencies=["M04"]),
            ]
        )
        m09_steps = plan.get_steps_by_module("M09")
        assert len(m09_steps) == 1
        assert m09_steps[0].module == "M09"

    def test_get_module_index(self):
        """测试获取模块索引"""
        plan = ExecutionPlan(
            plan_id="plan_12345678",
            workflow_type=WorkflowType.STANDARD,
            steps=[
                ExecutionStep(module="M04", mode=ExecutionMode.RUN_FULL),
                ExecutionStep(module="M09", mode=ExecutionMode.RUN_FULL, dependencies=["M04"]),
            ]
        )
        assert plan.get_module_index("M04") == 0
        assert plan.get_module_index("M09") == 1
        assert plan.get_module_index("M99") == -1

    def test_get_runnable_steps(self):
        """测试获取可运行步骤"""
        plan = ExecutionPlan(
            plan_id="plan_12345678",
            workflow_type=WorkflowType.STANDARD,
            steps=[
                ExecutionStep(module="M04", mode=ExecutionMode.RUN_FULL),
                ExecutionStep(module="M09", mode=ExecutionMode.RUN_FULL, dependencies=["M04"]),
                ExecutionStep(module="M10", mode=ExecutionMode.SKIP),
            ]
        )
        runnable = plan.get_runnable_steps(completed_modules=set())
        assert len(runnable) == 1
        assert runnable[0].module == "M04"

        runnable = plan.get_runnable_steps(completed_modules={"M04"})
        assert len(runnable) == 1
        assert runnable[0].module == "M09"


class TestWorkflowPlanner:
    """测试工作流规划器"""

    def test_init(self):
        """测试初始化"""
        planner = WorkflowPlanner()
        assert planner.dependency_resolver is not None
        assert "M01" in planner.estimated_durations
        assert "M09" in planner.estimated_durations

    def test_plan_quick_workflow(self):
        """测试规划快速工作流"""
        planner = WorkflowPlanner()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
            duration_seconds=1200,  # 20分钟
            subtitle=SubtitleStatus(
                exists=True,
                language="zh-CN",
                quality="verified",
            ),
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.COMPLETE),
            character_db=CapabilityEntry(
                state=CapabilityState.COMPLETE,
                coverage=1.0,
            ),
            voice_db=CapabilityEntry(
                state=CapabilityState.COMPLETE,
                coverage=1.0,
            ),
            story_db=CapabilityEntry(state=CapabilityState.NONE),
            translation_memory=CapabilityEntry(state=CapabilityState.NONE),
        )

        plan = planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=WorkflowType.QUICK
        )

        assert plan.workflow_type == WorkflowType.QUICK
        assert len(plan.steps) > 0
        assert plan.plan_id.startswith("plan_")

    def test_plan_standard_workflow(self):
        """测试规划标准工作流"""
        planner = WorkflowPlanner()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.PARTIAL),
            character_db=CapabilityEntry(state=CapabilityState.PARTIAL),
            voice_db=CapabilityEntry(state=CapabilityState.PARTIAL),
            story_db=CapabilityEntry(state=CapabilityState.NONE),
            translation_memory=CapabilityEntry(state=CapabilityState.NONE),
        )

        plan = planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=WorkflowType.STANDARD
        )

        assert plan.workflow_type == WorkflowType.STANDARD
        assert len(plan.steps) > 0

    def test_plan_production_workflow(self):
        """测试规划生产级工作流"""
        planner = WorkflowPlanner()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.NONE),
            character_db=CapabilityEntry(state=CapabilityState.NONE),
            voice_db=CapabilityEntry(state=CapabilityState.NONE),
            story_db=CapabilityEntry(state=CapabilityState.NONE),
            translation_memory=CapabilityEntry(state=CapabilityState.NONE),
        )

        plan = planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=WorkflowType.PRODUCTION
        )

        assert plan.workflow_type == WorkflowType.PRODUCTION
        # 生产级应该包含所有模块
        module_ids = {step.module for step in plan.steps}
        assert "M01" in module_ids
        assert "M14" in module_ids

    def test_plan_with_complete_character_db(self):
        """测试有完整人物库时的规划"""
        planner = WorkflowPlanner()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.COMPLETE),
            character_db=CapabilityEntry(
                state=CapabilityState.COMPLETE,
                coverage=1.0,
            ),
            voice_db=CapabilityEntry(state=CapabilityState.PARTIAL),
            story_db=CapabilityEntry(state=CapabilityState.NONE),
            translation_memory=CapabilityEntry(state=CapabilityState.NONE),
        )

        plan = planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=WorkflowType.STANDARD
        )

        # 查找 M04 步骤
        m04_steps = plan.get_steps_by_module("M04")
        # 完整的人物库应该跳过 M04
        assert len(m04_steps) == 0 or m04_steps[0].mode == ExecutionMode.SKIP

    def test_plan_with_partial_character_db(self):
        """测试部分人物库时的规划"""
        planner = WorkflowPlanner()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.COMPLETE),
            character_db=CapabilityEntry(
                state=CapabilityState.PARTIAL,
                coverage=0.75,  # 75% 覆盖率
            ),
            voice_db=CapabilityEntry(state=CapabilityState.PARTIAL),
            story_db=CapabilityEntry(state=CapabilityState.NONE),
            translation_memory=CapabilityEntry(state=CapabilityState.NONE),
        )

        plan = planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=WorkflowType.STANDARD
        )

        # 查找 M04 步骤
        m04_steps = plan.get_steps_by_module("M04")
        # 部分人物库应该增量运行
        assert len(m04_steps) > 0
        assert m04_steps[0].mode == ExecutionMode.RUN_INCREMENTAL

    def test_plan_with_verified_subtitle(self):
        """测试有验证字幕时的规划"""
        planner = WorkflowPlanner()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
            subtitle=SubtitleStatus(
                exists=True,
                language="zh-CN",
                quality="verified",
            ),
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.COMPLETE),
            character_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            voice_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            story_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            translation_memory=CapabilityEntry(state=CapabilityState.COMPLETE),
        )

        plan = planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=WorkflowType.STANDARD
        )

        # M03 应该跳过
        m03_steps = plan.get_steps_by_module("M03")
        assert len(m03_steps) == 0 or m03_steps[0].mode == ExecutionMode.SKIP

        # M06 翻译应该跳过
        m06_steps = plan.get_steps_by_module("M06")
        assert len(m06_steps) == 0 or m06_steps[0].mode == ExecutionMode.SKIP

    def test_plan_revoice_workflow(self):
        """测试重新配音工作流"""
        planner = WorkflowPlanner()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.REVOICE,
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.COMPLETE),
            character_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            voice_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            story_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            translation_memory=CapabilityEntry(state=CapabilityState.COMPLETE),
        )

        plan = planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=WorkflowType.REVOICE
        )

        assert plan.workflow_type == WorkflowType.REVOICE
        # REVOICE 应该从 M08 开始，不包含 M01-M07
        module_ids = {step.module for step in plan.steps}
        assert "M01" not in module_ids
        assert "M02" not in module_ids
        assert "M08" in module_ids

    def test_plan_rerender_workflow(self):
        """测试重新渲染工作流"""
        planner = WorkflowPlanner()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.RERENDER,
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.COMPLETE),
            character_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            voice_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            story_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            translation_memory=CapabilityEntry(state=CapabilityState.COMPLETE),
        )

        plan = planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=WorkflowType.RERENDER
        )

        assert plan.workflow_type == WorkflowType.RERENDER
        # RERENDER 只需要 M11-M13
        module_ids = {step.module for step in plan.steps}
        assert "M11" in module_ids
        assert "M12" in module_ids
        assert "M13" in module_ids
        # 不应该包含 M09
        assert "M09" not in module_ids

    def test_plan_qa_only_workflow(self):
        """测试仅质检工作流"""
        planner = WorkflowPlanner()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.QA,
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.COMPLETE),
            character_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            voice_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            story_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            translation_memory=CapabilityEntry(state=CapabilityState.COMPLETE),
        )

        plan = planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=WorkflowType.QA_ONLY
        )

        assert plan.workflow_type == WorkflowType.QA_ONLY
        # QA_ONLY 只需要 M13
        module_ids = {step.module for step in plan.steps}
        assert len(module_ids) == 1
        assert "M13" in module_ids

    def test_plan_with_existing_artifacts(self):
        """测试有已有 Artifact 时的规划"""
        planner = WorkflowPlanner()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.COMPLETE),
            character_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            voice_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            story_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            translation_memory=CapabilityEntry(state=CapabilityState.COMPLETE),
        )

        existing_artifacts = {
            "M04": CapabilityState.COMPLETE,  # M04 已有完整 Artifact
        }

        plan = planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=WorkflowType.STANDARD,
            existing_artifacts=existing_artifacts
        )

        # M04 应该是 LOAD 模式
        m04_steps = plan.get_steps_by_module("M04")
        if m04_steps:
            assert m04_steps[0].mode == ExecutionMode.LOAD

    def test_plan_with_failed_module(self):
        """测试从失败模块继续"""
        planner = WorkflowPlanner()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.COMPLETE),
            character_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            voice_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            story_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            translation_memory=CapabilityEntry(state=CapabilityState.COMPLETE),
        )

        plan = planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=WorkflowType.STANDARD,
            failed_module="M09"  # M09 失败
        )

        # 应该从 M09 开始，不包含 M09 之前的模块
        module_ids = [step.module for step in plan.steps]

        # 找到 M09 的位置
        if "M09" in module_ids:
            m09_index = module_ids.index("M09")
            # M09 之前的模块不应该出现
            before_m09 = module_ids[:m09_index]
            # 只保留失败点和之后的模块
            assert "M04" not in before_m09 or "M09" in before_m09

    def test_execution_order_respects_dependencies(self):
        """测试执行顺序尊重依赖关系"""
        planner = WorkflowPlanner()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.COMPLETE),
            character_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            voice_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            story_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            translation_memory=CapabilityEntry(state=CapabilityState.COMPLETE),
        )

        plan = planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=WorkflowType.STANDARD
        )

        # 验证依赖关系
        for step in plan.steps:
            for dep in step.dependencies:
                dep_index = plan.get_module_index(dep)
                step_index = plan.get_module_index(step.module)
                assert dep_index >= 0, f"依赖模块 {dep} 不在计划中"
                assert dep_index < step_index, f"依赖顺序错误：{dep} 应该在 {step.module} 之前"

    def test_estimated_duration(self):
        """测试预估时长计算"""
        planner = WorkflowPlanner()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.COMPLETE),
            character_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            voice_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            story_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            translation_memory=CapabilityEntry(state=CapabilityState.COMPLETE),
        )

        plan = planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=WorkflowType.STANDARD
        )

        # 总预估时长应该大于 0
        assert plan.total_estimated_duration > 0

        # 总时长应该等于所有 RUN_FULL 和 RUN_INCREMENTAL 步骤的时长之和
        expected_duration = sum(
            step.estimated_duration or 0
            for step in plan.steps
            if step.mode in [ExecutionMode.RUN_FULL, ExecutionMode.RUN_INCREMENTAL]
        )
        assert plan.total_estimated_duration == expected_duration

    def test_preview_workflow(self):
        """测试预览工作流"""
        planner = WorkflowPlanner()

        task_context = TaskContext(
            project_id="test",
            media_id="preview",
            task_type=TaskType.PREVIEW,
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.COMPLETE),
            character_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            voice_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            story_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            translation_memory=CapabilityEntry(state=CapabilityState.COMPLETE),
        )

        plan = planner.plan(
            task_context=task_context,
            capability_matrix=capability_matrix,
            workflow_type=WorkflowType.PREVIEW
        )

        assert plan.workflow_type == WorkflowType.PREVIEW
        # 预览应该跳过一些模块
        module_ids = {step.module for step in plan.steps}
        # 不应该包含 M14（归档）
        assert "M14" not in module_ids
