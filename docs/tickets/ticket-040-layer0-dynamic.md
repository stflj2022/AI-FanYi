# Ticket 040: Layer 0 动态调度完善（按冻结版 Layer 0）

## 状态: todo

## 优先级: P1

## 模块: Layer 0 Orchestrator

## 描述

按《计划书/ai-fanyi-00-2-冻结版layer 0.txt》完善 Layer 0：Task Context → Asset Discovery → Capability Matrix → Workflow Selector → Dependency Resolver → Planner → Executor 动态生成执行链（QUICK/STANDARD/PRODUCTION），不枚举组合，支持增量/缓存/跳过/恢复。Web UI 用户只需选语言/质量（自动/快速/标准/高质量），Layer 0 决定一切。

现有基础：TaskContext/AssetDiscovery/CapabilityMatrix/WorkflowSelector/DependencyResolver/WorkflowPlanner/WorkflowExecutor 已有实现（ticket-024~028）。

## 任务清单

- [ ] 将动态工作流（planner/executor）与 Job Runner 集成：Web 任务按资产状态生成最小执行链
- [ ] Workflow Selector 支持 QUICK/STANDARD/PRODUCTION（基于字幕/人物库/声音库存在性与覆盖率、视频长度、质量要求）
- [ ] 支持 LOAD/SKIP/RUN_INCREMENTAL（已有 artifact 复用、无字幕跳过等）
- [ ] 失败恢复/断点续跑：从失败模块继续
- [ ] 模块间通过 Artifact 传递（不直接调用）

## 验收标准

- 同一任务在"有字幕/有人物库"与"无字幕/无人物库"时生成不同的最小执行链
- 已有 artifact 的模块被 LOAD/SKIP，不重复计算
- 失败模块恢复后从该模块继续
