# Ticket 028: Layer 0 Workflow Executor 集成

## 状态: done（第1轮实现：WorkflowExecutor 已实现，集成调度器和 Artifact Registry，支持 checkpoint 和失败恢复，531 测试通过）

## 优先级: P0

## 模块: Layer 0 Orchestrator

## 描述

实现 Workflow Executor：执行 Planner 生成的 Execution Plan，严格采用 Module → Artifact → Checkpoint → 释放资源 → 下一个 Module。集成现有 scheduler DispatchEngine / worker_manager，替代 run_full_pipeline.py 的手动顺序编排。

参考：计划书 2 二十五、二十六节。

## 任务清单

- [ ] 实现 `workflow_executor.py`：WorkflowExecutor 类
- [ ] 集成现有 JobService / DispatchEngine / worker_manager
- [ ] 模块间通过 Artifact 通信（禁止直接调用）
- [ ] 执行计划含 Checkpoint（断点续跑）
- [ ] 更新 `run_full_pipeline.py` 使用新引擎（或提供等价入口）
- [ ] 编写端到端测试（不同输入状态产生不同执行链）

## 验收标准

- 能基于动态执行计划跑通 M01~M14
- 相同任务输入不同状态产生不同执行链（验证动态编排）
- 断点续跑从失败模块继续
- 端到端测试通过
