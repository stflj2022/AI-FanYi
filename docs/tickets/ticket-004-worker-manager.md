# Ticket 004: Worker 管理器实现

## 状态: todo（第3轮：先修测试套件再真实实现，驱动独立pytest验收）

## 优先级: 高

## 模块: Layer 0 Orchestrator

## 描述

实现 Worker 管理器，负责 Worker 注册、心跳监控、状态跟踪和指令下发。

## 任务清单

- [ ] 创建 `src/filmdub/orchestrator/worker_manager.py` - Worker 管理器
  - [ ] Worker 注册和认证
  - [ ] 心跳处理
  - [ ] 状态更新
  - [ ] 健康检查
  - [ ] 指令队列管理
  - [ ] Worker 下线处理
- [ ] 创建 `src/filmdub/apps/api/routers/workers.py` - Worker API
  - [ ] POST /api/v1/workers/register - Worker 注册
  - [ ] POST /api/v1/workers/{worker_id}/heartbeat - 心跳
  - [ ] GET /api/v1/workers - 获取 Worker 列表
  - [ ] GET /api/v1/workers/{worker_id} - 获取 Worker 详情
  - [ ] POST /api/v1/workers/{worker_id}/unregister - 注销 Worker
- [ ] 实现 JWT Token 生成和验证
- [ ] 实现心跳超时检测
- [ ] 实现指令下发机制
- [ ] 编写单元测试
- [ ] 编写集成测试（模拟 Worker）

## 依赖

- Ticket 001: 数据库模型
- Ticket 003: REST API 基础

## 输出

- Worker 管理器实现
- Worker API 端点
- JWT 认证逻辑
- 测试文件

## 验收标准

1. Worker 可以成功注册
2. 心跳机制正常工作
3. 超时 Worker 被正确检测
4. 指令可以正确下发
5. 测试通过

## 参考 ADR

- ADR 0006: Worker 通信协议
