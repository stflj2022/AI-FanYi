# Ticket 025: Layer 0 Capability Matrix

## 状态: done（第1轮实现：CapabilityMatrix 已实现，18 个测试通过）

## 优先级: P0

## 模块: Layer 0 Orchestrator

## 描述

实现计划书 2 的 Capability Matrix：每种资源的能力状态不是简单的"有/无"，而是 NONE / PARTIAL / COMPLETE / INVALID / OUTDATED 五态判定。这是动态工作流编排的核心基础。

参考：计划书 2 六、七节。

## 任务清单

- [ ] 实现 `capability_matrix.py`：CapabilityMatrix 数据结构
- [ ] 定义能力状态枚举（NONE/PARTIAL/COMPLETE/INVALID/OUTDATED）
- [ ] 实现各资源能力判定逻辑（人物库/声音库/字幕/Artifact 等，含覆盖率阈值）
- [ ] 实现从 AssetDiscovery 结果到 CapabilityMatrix 的转换
- [ ] 编写单元测试（test_capability_matrix.py）

## 验收标准

- 能对人物库/声音库/字幕等输出五态能力判定
- 覆盖率阈值可配置
- 测试通过
