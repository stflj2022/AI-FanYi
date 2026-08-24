# Ticket 024: Layer 0 Task Context + Asset Discovery

## 状态: todo

## 优先级: P0

## 模块: Layer 0 Orchestrator

## 描述

实现计划书 2 冻结版 Layer 0 的七阶段工作流引擎前两阶段：
1. **Task Context**：为每个任务构建统一的任务上下文（项目/媒体/字幕/人物库/声音库/故事库/翻译记忆/质量要求/首次处理标记等）
2. **Asset Discovery**：检查所有资源状态（视频/音频/字幕/人物库/声音库/故事库/翻译记忆/已有 Artifact），输出标准资产状态

参考：`/home/wu/桌面/AI-FanYi/计划书/ai-fanyi-00-2-冻结版layer 0.txt` 四、五节。

## 任务清单

- [ ] 创建 `src/filmdub/orchestrator/workflow/__init__.py`
- [ ] 实现 `task_context.py`：TaskContext 数据结构（含 subtitle/audio/character_db/voice_db/story_db/translation_memory 存在性与覆盖率、first_processing、quality_requirement、force_workflow）
- [ ] 实现 `asset_discovery.py`：扫描资源并生成 AssetStatus（不只看文件存在，检查版本/覆盖率/适用性）
- [ ] 编写单元测试（test_task_context.py, test_asset_discovery.py）

## 验收标准

- 给定不同项目状态，能生成一致的 TaskContext 和 AssetStatus
- 覆盖计划书中的核心状态（字幕有/无/已验证、人物库存在/覆盖率、任务类型等）
- 测试通过
