"""Dependency Resolver - 依赖解析器

基于 Capability Matrix 动态解析模块的前置依赖。
不是固定流水线，而是根据当前状态动态生成依赖图。

参考：计划书 2 十二、十三、三十一节
"""

from typing import Dict, List, Set, Optional
from pydantic import BaseModel

from .capability_matrix import CapabilityMatrix, CapabilityState
from .task_context import TaskContext


class ModuleDependency(BaseModel):
    """模块依赖定义"""
    module: str  # 模块 ID (M01-M14)
    requires: List[str] = []  # 前置模块列表
    requires_assets: List[str] = []  # 需要的资产类型
    min_capability: Dict[str, str] = {}  # 最低能力要求


class DependencyGraph(BaseModel):
    """依赖图"""
    nodes: Dict[str, ModuleDependency] = {}
    edges: Dict[str, List[str]] = {}  # 模块 -> 依赖的模块列表

    def get_dependencies(self, module: str) -> List[str]:
        """获取模块的所有依赖"""
        return self.edges.get(module, [])

    def add_dependency(self, module: str, depends_on: str):
        """添加依赖关系"""
        if module not in self.edges:
            self.edges[module] = []
        if depends_on not in self.edges[module]:
            self.edges[module].append(depends_on)

    def is_cyclic(self) -> bool:
        """检测是否存在循环依赖"""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in self.edges.keys()}
        path = []  # 用于记录路径

        def dfs(node: str) -> bool:
            # 如果节点不在 edges 中，跳过
            if node not in color:
                return False

            if color[node] == GRAY:
                # 发现环，打印循环路径
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                print(f"  检测到循环依赖: {' -> '.join(cycle)}")
                return True
            if color[node] == BLACK:
                return False  # 已处理

            color[node] = GRAY
            path.append(node)

            for neighbor in self.edges.get(node, []):
                if dfs(neighbor):
                    return True

            path.pop()
            color[node] = BLACK
            return False

        for node in self.edges.keys():
            if color[node] == WHITE:
                if dfs(node):
                    return True

        return False


class DependencyResolver:
    """依赖解析器

    根据当前能力状态动态解析模块依赖。
    """

    # 模块依赖定义（基础依赖）
    BASE_DEPENDENCIES = {
        "M02": {  # Project Research & Identity Resolution
            "requires": ["M01"],
            "requires_assets": ["video"],
        },
        "M03": {  # Subtitle & Dialogue Acquisition
            "requires": ["M01"],
            "requires_assets": ["video"],
        },
        "M04": {  # Character Database Construction
            "requires": ["M03"],
            "requires_assets": ["subtitle", "video"],
        },
        "M05": {  # Audio & Scene Analysis
            "requires": ["M01", "M02"],
            "requires_assets": ["video", "audio"],
        },
        "M06": {  # Speaker → Character Mapping
            "requires": ["M05", "M04"],
            "requires_assets": ["subtitle"],
        },
        "M07": {  # Subtitle / Dialogue Intelligence
            "requires": ["M06", "M04"],
            "requires_assets": ["subtitle", "character_db"],
        },
        "M08": {  # Prosody & Performance Planning
            "requires": ["M07"],
            "requires_assets": ["subtitle"],
        },
        "M09": {  # Voice Synthesis
            "requires": ["M08", "M04"],
            "requires_assets": ["voice_db", "character_db"],
        },
        "M10": {  # Dialogue Audio Processing & Scene Mixing
            "requires": ["M09", "M05"],
            "requires_assets": ["video", "audio"],
        },
        "M11": {  # Video Assembly & Final Encoding
            "requires": ["M10"],
            "requires_assets": ["video", "audio", "subtitle"],
        },
        "M12": {  # Project QA & Human Review
            "requires": ["M11"],
            "requires_assets": [],
        },
        "M13": {  # Batch / Season Pipeline
            "requires": ["M12"],
            "requires_assets": [],
        },
        "M14": {  # Project Archive & Reproducibility
            "requires": ["M13"],
            "requires_assets": [],
        },
    }

    def __init__(self):
        """初始化依赖解析器"""
        self.base_dependencies = self.BASE_DEPENDENCIES.copy()

    def resolve(
        self,
        modules: List[str],
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> DependencyGraph:
        """解析模块依赖

        Args:
            modules: 需要执行的模块列表
            task_context: 任务上下文
            capability_matrix: 能力矩阵

        Returns:
            DependencyGraph 依赖图
        """
        graph = DependencyGraph()

        # 为每个模块创建节点
        for module in modules:
            deps = self._resolve_module_dependencies(
                module,
                task_context,
                capability_matrix
            )
            graph.edges[module] = deps

        # 检测循环依赖
        if graph.is_cyclic():
            raise ValueError("检测到循环依赖")

        return graph

    def _resolve_module_dependencies(
        self,
        module: str,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> List[str]:
        """解析单个模块的依赖

        根据当前能力状态动态决定需要哪些前置模块。

        Args:
            module: 模块 ID
            task_context: 任务上下文
            capability_matrix: 能力矩阵

        Returns:
            依赖模块列表
        """
        if module not in self.base_dependencies:
            return []

        base_deps = self.base_dependencies[module]["requires"]
        required_assets = self.base_dependencies[module]["requires_assets"]

        dependencies = []

        # 检查基础依赖是否满足
        for dep in base_deps:
            if self._should_run_module(dep, task_context, capability_matrix):
                dependencies.append(dep)

        # 动态添加依赖（如果需要的资产不存在）
        for asset in required_assets:
            if not self._has_asset(asset, capability_matrix, task_context):
                # 添加能生成该资产的模块
                asset_producer = self._find_asset_producer(asset, task_context)
                if asset_producer and asset_producer not in dependencies:
                    dependencies.append(asset_producer)

        # 检查 Voice Profile（M09 依赖）
        if module == "M09":
            # 只有当声音库不存在时才需要 M04
            if not capability_matrix.has_capability("voice_db", CapabilityState.PARTIAL):
                # 声音库不存在或无效，需要运行 M04
                if "M04" not in dependencies:
                    dependencies.append("M04")

        # 检查人物映射（M07 依赖）
        if module == "M07":
            # 只有当人物库不存在时才需要 M04
            if not capability_matrix.has_capability("character_db", CapabilityState.PARTIAL):
                # 人物库不存在或无效，需要运行 M04
                if "M04" not in dependencies:
                    dependencies.append("M04")

        return dependencies

    def _should_run_module(
        self,
        module: str,
        task_context: TaskContext,
        capability_matrix: CapabilityMatrix
    ) -> bool:
        """判断模块是否需要运行"""
        # 如果模块不在基础依赖中，不运行
        if module not in self.base_dependencies:
            return False

        # M01 总是运行（项目媒体输入）
        if module == "M01":
            return True

        # M03：如果有已验证的可靠字幕，可以跳过
        if module == "M03":
            return not task_context.has_verified_subtitle()

        # M04：如果人物库完整，可以跳过
        if module == "M04":
            return not capability_matrix.has_capability("character_db", CapabilityState.COMPLETE)

        # M05：音频分析通常需要运行
        if module == "M05":
            return True

        # M06：如果有可靠字幕，可以跳过翻译
        if module == "M06" and task_context.has_verified_subtitle():
            return False

        # 其他模块默认需要运行
        return True

    def _has_asset(
        self,
        asset: str,
        capability_matrix: CapabilityMatrix,
        task_context: TaskContext
    ) -> bool:
        """检查资产是否存在"""
        if asset == "video":
            return capability_matrix.has_capability("video", CapabilityState.PARTIAL)
        elif asset == "audio":
            return capability_matrix.has_capability("audio", CapabilityState.PARTIAL)
        elif asset == "subtitle":
            return task_context.has_subtitle()
        elif asset == "character_db":
            return capability_matrix.has_capability("character_db", CapabilityState.PARTIAL)
        elif asset == "voice_db":
            return capability_matrix.has_capability("voice_db", CapabilityState.PARTIAL)
        elif asset == "story_db":
            return capability_matrix.has_capability("story_db", CapabilityState.PARTIAL)
        elif asset == "translation_memory":
            return capability_matrix.has_capability("translation_memory", CapabilityState.PARTIAL)
        return False

    def _find_asset_producer(self, asset: str, task_context: TaskContext) -> Optional[str]:
        """找到能生成指定资产的模块"""
        asset_producers = {
            "video": "M01",
            "audio": "M01",
            "subtitle": "M03",
            "character_db": "M04",
            "voice_db": "M04",
            "story_db": "M04",  # 简化：M04 也负责故事库
            "translation_memory": "M06",
        }
        return asset_producers.get(asset)

    def get_execution_order(self, graph: DependencyGraph) -> List[str]:
        """获取拓扑排序的执行顺序

        Args:
            graph: 依赖图

        Returns:
            拓扑排序的模块列表
        """
        # Kahn 算法
        in_degree = {node: 0 for node in graph.edges.keys()}
        for module, deps in graph.edges.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[module] += 1

        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            # 减少依赖此节点的其他节点的入度
            for module, deps in graph.edges.items():
                if node in deps:
                    in_degree[module] -= 1
                    if in_degree[module] == 0:
                        queue.append(module)

        if len(result) != len(graph.edges):
            raise ValueError("无法生成拓扑排序（可能存在循环依赖）")

        return result
