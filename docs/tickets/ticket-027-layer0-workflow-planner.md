# Ticket 027: Layer 0 Workflow Planner

## 状态: todo

## 优先级: P0

## 模块: Layer 0 Orchestrator

## 描述

实现 Workflow Planner：根据 Workflow + CapabilityMatrix + Dependency Graph + 已有 Artifact，生成执行计划（Execution Plan）。每个模块执行模式为 RUN_FULL / RUN_INCREMENTAL / LOAD / SKIP。

参考：计划书 2 十四、十五、十六~二十四节。

## 任务清单

- [ ] 实现 `dependency_resolver.py`（若 scheduler.py 已有则复用/扩展）：基于能力矩阵动态解析模块前置依赖
- [ ] 实现 `workflow_planner.py`：生成 ExecutionPlan（steps: module + mode）
- [ ] 实现四种执行模式判定（RUN_FULL/RUN_INCREMENTAL/LOAD/SKIP）
- [ ] 支持从失败模块继续（已有 Artifact 的模块 SKIP/LOAD）
- [ ] 编写单元测试（test_workflow_planner.py）

## 验收标准

- 不同能力矩阵产生不同执行计划（覆盖计划书十六~二十四节的各种场景）
- 支持增量（部分人物库 RUN_INCREMENTAL）、缓存（已有 Artifact LOAD）
- 测试通过
