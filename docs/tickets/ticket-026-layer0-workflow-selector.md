# Ticket 026: Layer 0 Workflow Selector

## 状态: todo

## 优先级: P0

## 模块: Layer 0 Orchestrator

## 描述

实现 Workflow Selector：基于规则引擎 + 打分 + 硬约束（第一版不使用 LLM 决策），根据 TaskContext + CapabilityMatrix 选择 QUICK / STANDARD / PRODUCTION 工作流。支持用户强制指定。

参考：计划书 2 九、十、三十七节。

## 任务清单

- [ ] 实现 `workflow_selector.py`：WorkflowSelector 类
- [ ] 定义工作流类型枚举（QUICK/STANDARD/PRODUCTION/PREVIEW/REVOICE/RERENDER/QA_ONLY）
- [ ] 实现规则引擎（决策优先级：用户明确要求 > 任务类型 > 已有资产 > 资产质量 > 字幕状态 > 视频长度）
- [ ] 实现用户强制模式 + 推荐原因说明
- [ ] 创建 `layer0/workflows/quick.yaml`、`standard.yaml`、`production.yaml` 等配置
- [ ] 编写单元测试（test_workflow_selector.py）

## 验收标准

- 相同输入产生相同决策（可测试）
- 支持用户强制指定工作流
- 测试通过
