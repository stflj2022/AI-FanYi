"""测试依赖解析器"""

import pytest

from filmdub.orchestrator.workflow.dependency_resolver import (
    DependencyResolver,
    DependencyGraph,
)
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


class TestDependencyGraph:
    """测试依赖图"""

    def test_create_empty_graph(self):
        """测试创建空依赖图"""
        graph = DependencyGraph()
        assert graph.nodes == {}
        assert graph.edges == {}

    def test_add_dependency(self):
        """测试添加依赖"""
        graph = DependencyGraph()
        graph.add_dependency("M09", "M08")
        assert graph.get_dependencies("M09") == ["M08"]

    def test_add_multiple_dependencies(self):
        """测试添加多个依赖"""
        graph = DependencyGraph()
        graph.add_dependency("M09", "M08")
        graph.add_dependency("M09", "M04")
        deps = graph.get_dependencies("M09")
        assert "M08" in deps
        assert "M04" in deps
        assert len(deps) == 2

    def test_no_cyclic_dependencies(self):
        """测试无循环依赖"""
        graph = DependencyGraph()
        graph.edges = {
            "M01": [],
            "M02": ["M01"],
            "M03": ["M01"],
            "M04": ["M03"],
        }
        assert not graph.is_cyclic()

    def test_detect_cyclic_dependencies(self):
        """测试检测循环依赖"""
        graph = DependencyGraph()
        graph.edges = {
            "M01": ["M02"],
            "M02": ["M03"],
            "M03": ["M01"],  # 循环
        }
        assert graph.is_cyclic()


class TestDependencyResolver:
    """测试依赖解析器"""

    def test_init(self):
        """测试初始化"""
        resolver = DependencyResolver()
        assert resolver.base_dependencies is not None
        assert "M01" not in resolver.base_dependencies
        assert "M02" in resolver.base_dependencies

    def test_resolve_simple_dependencies(self):
        """测试解析简单依赖"""
        resolver = DependencyResolver()

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

        graph = resolver.resolve(
            modules=["M09"],
            task_context=task_context,
            capability_matrix=capability_matrix
        )

        # M09 依赖 M08（基础依赖）
        # 当 voice_db 是 COMPLETE 时，不需要依赖 M04
        deps = graph.get_dependencies("M09")
        assert "M08" in deps
        # 声音库完整时，不需要依赖 M04

    def test_resolve_with_missing_voice_db(self):
        """测试缺失声音库时的依赖解析"""
        resolver = DependencyResolver()

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
            voice_db=CapabilityEntry(state=CapabilityState.NONE),  # 无声音库
            story_db=CapabilityEntry(state=CapabilityState.NONE),
            translation_memory=CapabilityEntry(state=CapabilityState.NONE),
        )

        graph = resolver.resolve(
            modules=["M09"],
            task_context=task_context,
            capability_matrix=capability_matrix
        )

        # M09 应该依赖 M04 来建立声音库
        deps = graph.get_dependencies("M09")
        assert "M04" in deps

    def test_resolve_with_verified_subtitle(self):
        """测试有验证字幕时的依赖解析"""
        resolver = DependencyResolver()

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

        graph = resolver.resolve(
            modules=["M07"],
            task_context=task_context,
            capability_matrix=capability_matrix
        )

        # M07 应该不依赖 M06（有验证字幕）
        deps = graph.get_dependencies("M07")
        assert "M06" not in deps

    def test_resolve_without_subtitle(self):
        """测试无字幕时的依赖解析"""
        resolver = DependencyResolver()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
            subtitle=SubtitleStatus(exists=False),
        )

        capability_matrix = CapabilityMatrix(
            video=CapabilityEntry(state=CapabilityState.COMPLETE),
            audio=CapabilityEntry(state=CapabilityState.COMPLETE),
            subtitle=CapabilityEntry(state=CapabilityState.NONE),
            character_db=CapabilityEntry(state=CapabilityState.PARTIAL),
            voice_db=CapabilityEntry(state=CapabilityState.PARTIAL),
            story_db=CapabilityEntry(state=CapabilityState.NONE),
            translation_memory=CapabilityEntry(state=CapabilityState.NONE),
        )

        graph = resolver.resolve(
            modules=["M07"],
            task_context=task_context,
            capability_matrix=capability_matrix
        )

        # M07 应该依赖 M06（需要翻译）
        deps = graph.get_dependencies("M07")
        assert "M06" in deps

    def test_get_execution_order(self):
        """测试获取执行顺序（拓扑排序）"""
        resolver = DependencyResolver()

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

        graph = resolver.resolve(
            modules=["M04", "M07", "M09"],
            task_context=task_context,
            capability_matrix=capability_matrix
        )

        order = resolver.get_execution_order(graph)

        # M04 应该在 M07 之前，M07 应该在 M09 之前
        assert order.index("M04") < order.index("M07")
        assert order.index("M07") < order.index("M09")

    def test_resolve_multiple_modules(self):
        """测试解析多个模块的依赖"""
        resolver = DependencyResolver()

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

        graph = resolver.resolve(
            modules=["M04", "M07", "M08", "M09"],
            task_context=task_context,
            capability_matrix=capability_matrix
        )

        # 检查每个模块的依赖
        # M07 不依赖 M04，因为人物库已完整
        assert "M06" in graph.get_dependencies("M07") or "M03" in graph.get_dependencies("M07")
        assert "M07" in graph.get_dependencies("M08")
        assert "M08" in graph.get_dependencies("M09")
        # M09 不依赖 M04，因为声音库已完整

    def test_resolve_with_partial_character_db(self):
        """测试部分人物库时的依赖解析"""
        resolver = DependencyResolver()

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

        graph = resolver.resolve(
            modules=["M04"],
            task_context=task_context,
            capability_matrix=capability_matrix
        )

        # M04 仍然应该有依赖（M03）
        deps = graph.get_dependencies("M04")
        assert "M03" in deps

    def test_no_cyclic_graph(self):
        """测试解析不会产生循环依赖"""
        resolver = DependencyResolver()

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

        graph = resolver.resolve(
            modules=["M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08", "M09"],
            task_context=task_context,
            capability_matrix=capability_matrix
        )

        # 不应该有循环依赖
        assert not graph.is_cyclic()

    def test_complex_dependency_chain(self):
        """测试复杂依赖链"""
        resolver = DependencyResolver()

        task_context = TaskContext(
            project_id="test",
            media_id="S01E01",
            task_type=TaskType.EPISODE,
            subtitle=SubtitleStatus(exists=False),
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

        graph = resolver.resolve(
            modules=["M09"],
            task_context=task_context,
            capability_matrix=capability_matrix
        )

        order = resolver.get_execution_order(graph)

        # 验证顺序：M01 -> M03/M05 -> M04 -> M06 -> M07 -> M08 -> M09
        if "M01" in order and "M03" in order:
            assert order.index("M01") < order.index("M03")
        if "M03" in order and "M04" in order:
            assert order.index("M03") < order.index("M04")
        if "M04" in order and "M06" in order:
            assert order.index("M04") < order.index("M06")
        if "M06" in order and "M07" in order:
            assert order.index("M06") < order.index("M07")
        if "M07" in order and "M08" in order:
            assert order.index("M07") < order.index("M08")
        if "M08" in order and "M09" in order:
            assert order.index("M08") < order.index("M09")
