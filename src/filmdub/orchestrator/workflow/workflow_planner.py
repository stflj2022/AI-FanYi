"""Workflow Planner - 工作流规划器

根据 Workflow + CapabilityMatrix + Dependency Graph + 已有 Artifact，
生成执行计划（Execution Plan）。

每个模块执行模式：
- RUN_FULL: 整个模块重新处理
- RUN_INCREMENTAL: 只处理缺失部分
- LOAD: 直接加载已有 Artifact
- SKIP: 完全不需要

参考：计划书 2 十四、十五、十六~二十四节
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field

from .task_context import TaskContext, TaskType
from .capability_matrix import CapabilityMatrix, CapabilityState
from .workflow_selector import WorkflowType
from .dependency_resolver import DependencyResolver, DependencyGraph


class ExecutionMode(str, Enum):
    """执行模式"""
    RUN_FULL = "run_full"  # 完整运行
    RUN_INCREMENTAL = "run_incremental"  # 增量运行
    LOAD = "load"  # 加载已有 Artifact
    SKIP = "skip"  # 跳过


class ExecutionStep(BaseModel):
    """执行步骤"""
    module: str  # 模块 ID (M01-M14)
    mode: ExecutionMode  # 执行模式
    dependencies: List[str] = []  # 前置步骤
    reason: str = ""  # 选择此模式的理由
    estimated_duration: Optional[float] = None  # 预估时长（秒）


class ExecutionPlan(BaseModel):
    """执行计划

    定义模块的执行顺序和模式。
    """
    plan_id: str
    workflow_type: WorkflowType
    steps: List[ExecutionStep] = []
    total_estimated_duration: float = 0.0
    metadata: Dict = Field(default_factory=dict)

    def get_steps_by_module(self, module: str) -> List[ExecutionStep]:
        """获取指定模块的所有步骤"""
        return [step for step in self.steps if step.module == module]

    def get_runnable_steps(self, completed_modules: Set[str]) -> List[ExecutionStep]:
        """获取当前可运行的步骤（依赖已完成）"""
        runnable = []
        for step in self.steps:
            if step.module in completed_modules:
                continue
            if step.mode == ExecutionMode.SKIP:
                continue
            # 检查依赖
            if all(dep in completed_modules for dep in step.dependencies):
                runnable.append(step)
        return runnable

    def get_module_index(self, module: str) -> int:
        """获取模块在计划中的索引"""
        for i, step in enumerate(self.steps):
            if step.module == module:
                return i
        return -1


class WorkflowPlanner:
    """工作流规划器

    生成最优的执行计划。
    """

    def __init__(self, dependency_resolver: Optional[DependencyResolver] = None):
        """初始化规划器

        Args:
            dependency_resolver: 依赖解析器
        """
        self.dependency_resolver = dependency_resolver or DependencyResolver()

        # 模块预估时长（秒）- 可根据实际情况调整
        self.estimated_durations = {
            "M01": 300,  # 5分钟
            "M02": 600,  # 10分钟
            "M03": 300,  # 5分钟
            "M04": 900,  # 15分钟
            "M05": 1800,  # 30分钟
            "M06": 600,  # 10分钟
            "M07": 300,  # 5分钟
            "M08": 600,  # 10分钟
            "M09": 3600,  # 60分钟（取决于视频长度）
            "M10": 1200,  # 20分钟
            "M11": 600,  # 10分钟
            "M12": 300,  # 5分钟
            "M13": 1200,  # 20分钟
            "M14": 600,  # 10分钟
        }

    def plan(
        self,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix,
        workflow_type: WorkflowType,
        existing_artifacts: Dict[str, CapabilityState] = None,
        failed_module: Optional[str] = None
    ) -> ExecutionPlan:
        """生成执行计划

        Args:
            task_context: 任务上下文
            capability_matrix: 能力矩阵
            workflow_type: 工作流类型
            existing_artifacts: 已存在的 Artifact
            failed_module: 失败的模块（用于从失败点继续）

        Returns:
            ExecutionPlan 执行计划
        """
        existing_artifacts = existing_artifacts or {}

        # 1. 确定需要执行的模块
        required_modules = self._determine_required_modules(
            workflow_type,
            task_context,
            capability_matrix
        )

        # 2. 解析依赖
        dependency_graph = self.dependency_resolver.resolve(
            required_modules,
            task_context,
            capability_matrix
        )

        # 3. 获取执行顺序
        execution_order = self.dependency_resolver.get_execution_order(dependency_graph)

        # 4. 为每个模块确定执行模式
        steps = []
        completed_modules = set()

        for module in execution_order:
            # 如果有失败模块，跳过它之前的模块
            if failed_module and self._is_before(module, failed_module, execution_order):
                completed_modules.add(module)
                continue

            # 确定执行模式
            mode, reason = self._determine_execution_mode(
                module,
                task_context,
                capability_matrix,
                existing_artifacts,
                completed_modules
            )

            # 获取依赖
            dependencies = dependency_graph.get_dependencies(module)
            # 只包含尚未完成且在执行计划中的依赖
            dependencies = [d for d in dependencies if d not in completed_modules and d in execution_order]

            # 创建步骤
            step = ExecutionStep(
                module=module,
                mode=mode,
                dependencies=dependencies,
                reason=reason,
                estimated_duration=self.estimated_durations.get(module, 600)
            )

            steps.append(step)

            # 如果是 SKIP 或 LOAD，标记为已完成
            if mode in [ExecutionMode.SKIP, ExecutionMode.LOAD]:
                completed_modules.add(module)

        # 5. 计算总预估时长
        total_duration = sum(
            step.estimated_duration or 0
            for step in steps
            if step.mode in [ExecutionMode.RUN_FULL, ExecutionMode.RUN_INCREMENTAL]
        )

        # 6. 生成计划 ID
        import uuid
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        return ExecutionPlan(
            plan_id=plan_id,
            workflow_type=workflow_type,
            steps=steps,
            total_estimated_duration=total_duration,
            metadata={
                "task_type": task_context.task_type.value,
                "video_length": task_context.duration_seconds,
                "failed_module": failed_module,
            }
        )

    def _determine_required_modules(
        self,
        workflow_type: WorkflowType,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> List[str]:
        """确定需要执行的模块列表

        根据工作流类型决定需要哪些模块。
        """
        if workflow_type == WorkflowType.QUICK:
            return self._get_quick_modules(task_context, capability_matrix)
        elif workflow_type == WorkflowType.STANDARD:
            return self._get_standard_modules(task_context, capability_matrix)
        elif workflow_type == WorkflowType.PRODUCTION:
            return self._get_production_modules(task_context, capability_matrix)
        elif workflow_type == WorkflowType.PREVIEW:
            return self._get_preview_modules(task_context, capability_matrix)
        elif workflow_type == WorkflowType.REVOICE:
            return self._get_revoice_modules(task_context, capability_matrix)
        elif workflow_type == WorkflowType.RERENDER:
            return self._get_rerender_modules(task_context, capability_matrix)
        elif workflow_type == WorkflowType.QA_ONLY:
            return self._get_qa_modules(task_context, capability_matrix)
        else:
            return self._get_standard_modules(task_context, capability_matrix)

    def _get_quick_modules(self, task_context: TaskContext, capability_matrix: CapabilityMatrix) -> List[str]:
        """快速工作流模块"""
        # 20分钟以下 + 有字幕 + 有人物库 + 有声音库
        modules = ["M01", "M05"]

        # 如果没有字幕，需要 M06 翻译
        if not task_context.has_verified_subtitle():
            modules.append("M06")

        # 如果没有人物库/声音库，需要 M04
        if not capability_matrix.has_capability("character_db", CapabilityState.COMPLETE):
            modules.insert(-1, "M04")

        # 基础流程
        modules.extend(["M07", "M08", "M09", "M10", "M11", "M12", "M13"])

        return modules

    def _get_standard_modules(self, task_context: TaskContext, capability_matrix: CapabilityMatrix) -> List[str]:
        """标准工作流模块"""
        modules = ["M01", "M02"]

        # 如果没有字幕，需要 M03
        if not task_context.has_subtitle():
            modules.append("M03")

        # 如果没有人物库/声音库，需要 M04
        if not capability_matrix.has_capability("character_db", CapabilityState.COMPLETE):
            modules.append("M04")

        # 基础流程
        modules.extend(["M05", "M07", "M08", "M09", "M10", "M11", "M12", "M13"])

        return modules

    def _get_production_modules(self, task_context: TaskContext, capability_matrix: CapabilityMatrix) -> List[str]:
        """生产级工作流模块（完整流程）"""
        return [
            "M01", "M02", "M03", "M04", "M05",
            "M06", "M07", "M08", "M09", "M10",
            "M11", "M12", "M13", "M14"
        ]

    def _get_preview_modules(self, task_context: TaskContext, capability_matrix: CapabilityMatrix) -> List[str]:
        """预览工作流模块（只测试片段）"""
        # 简化的预览流程
        modules = ["M01"]

        # 如果没有人物库，需要 M04
        if not capability_matrix.has_capability("character_db", CapabilityState.COMPLETE):
            modules.append("M04")

        # 核心 TTS 流程
        modules.extend(["M07", "M08", "M09", "M10", "M11"])

        return modules

    def _get_revoice_modules(self, task_context: TaskContext, capability_matrix: CapabilityMatrix) -> List[str]:
        """重新配音工作流模块"""
        # 已有 Dialogue，只需更新 Voice Profile 并重新 TTS
        modules = ["M08", "M09", "M10", "M11", "M12", "M13"]
        return modules

    def _get_rerender_modules(self, task_context: TaskContext, capability_matrix: CapabilityMatrix) -> List[str]:
        """重新渲染工作流模块"""
        # 不重新生成 TTS，只重新编码
        modules = ["M11", "M12", "M13"]
        return modules

    def _get_qa_modules(self, task_context: TaskContext, capability_matrix: CapabilityMatrix) -> List[str]:
        """仅质检工作流模块"""
        return ["M13"]

    def _determine_execution_mode(
        self,
        module: str,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix,
        existing_artifacts: Dict[str, CapabilityState],
        completed_modules: Set[str]
    ) -> tuple[ExecutionMode, str]:
        """确定模块的执行模式

        Args:
            module: 模块 ID
            task_context: 任务上下文
            capability_matrix: 能力矩阵
            existing_artifacts: 已存在的 Artifact
            completed_modules: 已完成的模块

        Returns:
            (执行模式, 理由)
        """
        # 检查是否有可用的 Artifact
        artifact_state = existing_artifacts.get(module)
        if artifact_state == CapabilityState.COMPLETE:
            # Artifact 完整，可以加载
            return ExecutionMode.LOAD, f"已有完整 {module} Artifact，直接加载"

        # 检查模块能力状态
        if module == "M04":  # 人物库
            if capability_matrix.has_capability("character_db", CapabilityState.COMPLETE):
                return ExecutionMode.SKIP, "人物库完整，跳过"
            elif capability_matrix.has_capability("character_db", CapabilityState.PARTIAL):
                return ExecutionMode.RUN_INCREMENTAL, f"人物库覆盖率 {capability_matrix.character_db.coverage:.0%}，增量更新"
            else:
                return ExecutionMode.RUN_FULL, "人物库不存在，完整建立"

        elif module == "M03":  # 字幕获取
            if task_context.has_verified_subtitle():
                return ExecutionMode.SKIP, "已有验证字幕，跳过"
            elif task_context.has_subtitle():
                return ExecutionMode.LOAD, "已有字幕，加载"
            else:
                return ExecutionMode.RUN_FULL, "无字幕，完整获取"

        elif module == "M06":  # 翻译
            if task_context.has_verified_subtitle():
                return ExecutionMode.SKIP, "已有验证中文字幕，跳过翻译"
            else:
                return ExecutionMode.RUN_FULL, "需要翻译对白"

        elif module == "M09":  # TTS
            if capability_matrix.has_capability("voice_db", CapabilityState.COMPLETE):
                return ExecutionMode.RUN_FULL, "声音库完整，完整合成"
            elif capability_matrix.has_capability("voice_db", CapabilityState.PARTIAL):
                return ExecutionMode.RUN_INCREMENTAL, f"声音库覆盖率 {capability_matrix.voice_db.coverage:.0%}，增量合成"
            else:
                return ExecutionMode.RUN_FULL, "声音库不存在，完整合成"

        else:
            # 默认完整运行
            return ExecutionMode.RUN_FULL, f"{module} 完整运行"

    def _is_before(self, module_a: str, module_b: str, execution_order: List[str]) -> bool:
        """判断 module_a 是否在 module_b 之前"""
        try:
            return execution_order.index(module_a) < execution_order.index(module_b)
        except ValueError:
            return False
