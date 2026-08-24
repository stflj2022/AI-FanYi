"""测试工作流执行器"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

from filmdub.orchestrator.workflow.workflow_executor import (
    WorkflowExecutor,
    ExecutionState,
)
from filmdub.orchestrator.workflow.workflow_planner import (
    ExecutionPlan,
    ExecutionStep,
    ExecutionMode,
)
from filmdub.orchestrator.workflow.task_context import TaskContext, TaskType
from filmdub.orchestrator.workflow.capability_matrix import CapabilityMatrix, CapabilityEntry, CapabilityState
from filmdub.orchestrator.workflow.workflow_selector import WorkflowType


class TestExecutionState:
    """测试执行状态"""

    def test_create_state(self):
        """测试创建执行状态"""
        state = ExecutionState()
        assert len(state.completed_steps) == 0
        assert len(state.failed_steps) == 0
        assert state.current_step is None
        assert len(state.artifacts) == 0

    def test_mark_step_completed(self):
        """测试标记步骤完成"""
        state = ExecutionState()
        artifact_path = Path("/tmp/artifact.json")

        state.mark_step_completed("M09", artifact_path)

        assert "M09" in state.completed_steps
        assert state.artifacts["M09"] == artifact_path

    def test_mark_step_failed(self):
        """测试标记步骤失败"""
        state = ExecutionState()
        state.mark_step_failed("M09")
        assert "M09" in state.failed_steps

    def test_is_step_completed(self):
        """测试检查步骤是否完成"""
        state = ExecutionState()
        assert not state.is_step_completed("M09")

        state.mark_step_completed("M09")
        assert state.is_step_completed("M09")

    def test_get_checkpoint(self):
        """测试获取检查点"""
        state = ExecutionState()
        state.mark_step_completed("M09", Path("/tmp/artifact.json"))
        state.current_step = "M10"
        state.start_time = datetime(2026, 1, 1, 12, 0, 0)

        checkpoint = state.get_checkpoint()

        assert "M09" in checkpoint["completed_steps"]
        assert checkpoint["current_step"] == "M10"
        assert checkpoint["start_time"] == "2026-01-01T12:00:00"

    def test_load_checkpoint(self):
        """测试加载检查点"""
        state = ExecutionState()
        checkpoint_data = {
            "completed_steps": ["M09"],
            "failed_steps": [],
            "current_step": "M10",
            "artifacts": {"M09": "/tmp/artifact.json"},
            "start_time": "2026-01-01T12:00:00",
        }

        state.load_checkpoint(checkpoint_data)

        assert "M09" in state.completed_steps
        assert state.current_step == "M10"
        assert str(state.artifacts["M09"]) == "/tmp/artifact.json"


class TestWorkflowExecutor:
    """测试工作流执行器"""

    @pytest.fixture
    def db(self):
        """模拟数据库会话"""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def artifact_registry(self):
        """模拟 Artifact 注册表"""
        registry = AsyncMock()
        registry.create_artifact = AsyncMock()
        registry.list_artifacts = AsyncMock(return_value=[])
        return registry

    @pytest.fixture
    def executor(self, db, artifact_registry, tmp_path):
        """创建执行器"""
        return WorkflowExecutor(
            db=db,
            artifact_registry=artifact_registry,
            project_root=tmp_path,
        )

    @pytest.fixture
    def task_context(self):
        """创建任务上下文"""
        return TaskContext(
            project_id="test_project",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
        )

    @pytest.fixture
    def capability_matrix(self):
        """创建能力矩阵"""
        return CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.COMPLETE),
            character_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            voice_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            story_db=CapabilityEntry(state=CapabilityState.COMPLETE),
            translation_memory=CapabilityEntry(state=CapabilityState.COMPLETE),
        )

    @pytest.fixture
    def execution_plan(self):
        """创建执行计划"""
        return ExecutionPlan(
            plan_id="plan_test",
            workflow_type=WorkflowType.QUICK,
            steps=[
                ExecutionStep(
                    module="M09",
                    mode=ExecutionMode.RUN_FULL,
                    dependencies=["M08"],
                    estimated_duration=3600,
                ),
                ExecutionStep(
                    module="M10",
                    mode=ExecutionMode.RUN_FULL,
                    dependencies=["M09"],
                    estimated_duration=1200,
                ),
            ],
        )

    def test_init(self, executor, db, artifact_registry, tmp_path):
        """测试初始化"""
        assert executor.db is db
        assert executor.artifact_registry is artifact_registry
        assert executor.project_root == tmp_path
        assert isinstance(executor.state, ExecutionState)

    @pytest.mark.asyncio
    async def test_execute_skip_mode(self, executor, task_context, capability_matrix):
        """测试执行 SKIP 模式的步骤"""
        plan = ExecutionPlan(
            plan_id="plan_skip",
            workflow_type=WorkflowType.QUICK,
            steps=[
                ExecutionStep(
                    module="M09",
                    mode=ExecutionMode.SKIP,
                    dependencies=[],
                ),
            ],
        )

        result = await executor.execute(plan, task_context, capability_matrix)

        assert result["status"] == "completed"
        assert "M09" in result["completed_steps"]
        assert len(result["failed_steps"]) == 0

    @pytest.mark.asyncio
    async def test_execute_with_dependencies(self, executor, task_context, capability_matrix):
        """测试执行有依赖的步骤"""
        # 先标记依赖完成
        executor.state.mark_step_completed("M08")

        plan = ExecutionPlan(
            plan_id="plan_deps",
            workflow_type=WorkflowType.QUICK,
            steps=[
                ExecutionStep(
                    module="M09",
                    mode=ExecutionMode.RUN_FULL,
                    dependencies=["M08"],
                ),
            ],
        )

        # Mock Worker 查找
        mock_worker = MagicMock()
        mock_worker.id = uuid.uuid4()
        mock_worker.worker_type = "voice_synthesis"

        self.db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=mock_worker)

        # 这个测试需要更多的 mock 设置
        # 这里只是基本框架
        pass

    def test_module_worker_map(self):
        """测试模块到 Worker 的映射"""
        assert WorkflowExecutor.MODULE_WORKER_MAP["M09"] == "voice_synthesis"
        assert WorkflowExecutor.MODULE_WORKER_MAP["M04"] == "character_db"
        assert WorkflowExecutor.MODULE_WORKER_MAP["M01"] == "media_intake"

    def test_are_dependencies_met(self, executor, execution_plan):
        """测试依赖检查"""
        step = execution_plan.steps[0]  # M09, 依赖 M08

        # 依赖未满足
        assert not executor._are_dependencies_met(step, execution_plan)

        # 标记依赖完成
        executor.state.mark_step_completed("M08")

        # 依赖满足
        assert executor._are_dependencies_met(step, execution_plan)

    @pytest.mark.asyncio
    async def test_save_checkpoint(self, executor, task_context, tmp_path):
        """测试保存检查点"""
        executor.state.mark_step_completed("M09", tmp_path / "artifact.json")
        executor.state.current_step = "M10"

        await executor._save_checkpoint(task_context.project_id)

        checkpoint_path = tmp_path / str(task_context.project_id) / "checkpoint.json"
        assert checkpoint_path.exists()

        import json
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)

        assert "M09" in checkpoint["completed_steps"]
        assert checkpoint["current_step"] == "M10"

    @pytest.mark.asyncio
    async def test_load_checkpoint(self, executor, task_context, tmp_path):
        """测试加载检查点"""
        # 先保存检查点
        executor.state.mark_step_completed("M09", tmp_path / "artifact.json")
        executor.state.current_step = "M10"
        await executor._save_checkpoint(task_context.project_id)

        # 创建新的执行器并加载检查点
        new_state = ExecutionState()
        checkpoint_path = tmp_path / str(task_context.project_id) / "checkpoint.json"
        import json
        with open(checkpoint_path) as f:
            checkpoint_data = json.load(f)
        new_state.load_checkpoint(checkpoint_data)

        assert "M09" in new_state.completed_steps
        assert new_state.current_step == "M10"

    def test_get_step_artifacts(self, execution_plan):
        """测试获取步骤 Artifact"""
        plan = ExecutionPlan(
            plan_id="plan_artifacts",
            workflow_type=WorkflowType.QUICK,
            steps=[
                ExecutionStep(module="M09", mode=ExecutionMode.RUN_FULL, dependencies=[]),
                ExecutionStep(module="M10", mode=ExecutionMode.RUN_FULL, dependencies=["M09"]),
            ],
        )

        steps = plan.get_steps_by_module("M09")
        assert len(steps) == 1
        assert steps[0].module == "M09"

    def test_get_runnable_steps(self, execution_plan):
        """测试获取可运行步骤"""
        plan = ExecutionPlan(
            plan_id="plan_runnable",
            workflow_type=WorkflowType.QUICK,
            steps=[
                ExecutionStep(module="M09", mode=ExecutionMode.RUN_FULL, dependencies=[]),
                ExecutionStep(module="M10", mode=ExecutionMode.RUN_FULL, dependencies=["M09"]),
                ExecutionStep(module="M11", mode=ExecutionMode.SKIP, dependencies=[]),
            ],
        )

        runnable = plan.get_runnable_steps(completed_modules=set())
        assert len(runnable) == 1
        assert runnable[0].module == "M09"

        runnable = plan.get_runnable_steps(completed_modules={"M09"})
        assert len(runnable) == 1
        assert runnable[0].module == "M10"

    @pytest.mark.asyncio
    async def test_execute_from_checkpoint(self, executor, task_context, capability_matrix, tmp_path):
        """测试从检查点恢复执行"""
        # 先保存检查点
        executor.state.mark_step_completed("M08")
        executor.state.mark_step_completed("M09")
        await executor._save_checkpoint(task_context.project_id)

        # 创建新的执行器并恢复
        new_executor = WorkflowExecutor(
            db=executor.db,
            artifact_registry=executor.artifact_registry,
            project_root=tmp_path,
        )

        plan = ExecutionPlan(
            plan_id="plan_resume",
            workflow_type=WorkflowType.QUICK,
            steps=[
                ExecutionStep(module="M08", mode=ExecutionMode.RUN_FULL, dependencies=[]),
                ExecutionStep(module="M09", mode=ExecutionMode.RUN_FULL, dependencies=["M08"]),
                ExecutionStep(module="M10", mode=ExecutionMode.RUN_FULL, dependencies=["M09"]),
            ],
        )

        result = await new_executor.execute(
            plan,
            task_context,
            capability_matrix,
            resume_from_checkpoint=True,
        )

        assert result["status"] == "completed"
        # M08 和 M09 应该被跳过（已完成）
        assert "M10" in result["completed_steps"]

    @pytest.mark.asyncio
    async def test_execute_with_failure(self, executor, task_context, capability_matrix):
        """测试执行失败的处理"""
        plan = ExecutionPlan(
            plan_id="plan_failure",
            workflow_type=WorkflowType.QUICK,
            steps=[
                ExecutionStep(module="M09", mode=ExecutionMode.RUN_FULL, dependencies=[]),
            ],
        )

        # Mock _run_module 抛出异常
        with patch.object(executor, "_run_module", side_effect=Exception("Test error")):
            with pytest.raises(Exception):
                await executor.execute(plan, task_context, capability_matrix)

        # 检查失败状态
        assert "M09" in executor.state.failed_steps

    def test_get_module_index(self, execution_plan):
        """测试获取模块索引"""
        assert execution_plan.get_module_index("M09") == 0
        assert execution_plan.get_module_index("M10") == 1
        assert execution_plan.get_module_index("M99") == -1
