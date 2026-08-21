# Ticket 015: WebSocket 实时通信

## 状态: todo（第3轮：先修测试套件再真实实现，驱动独立pytest验收）

## 优先级: 中

## 模块: Layer 0 Orchestrator

## 描述

实现 WebSocket 实时通信，支持作业进度推送、系统事件通知和 Worker 状态更新。

## 任务清单

### 后端部分
- [ ] 创建 `src/filmdub/apps/api/websocket/handler.py` - WebSocket 处理器
  - [ ] 连接管理
  - [ ] 消息广播
  - [ ] 频道订阅
- [ ] 创建 `src/filmdub/apps/api/websocket/manager.py` - 连接管理器
  - [ ] ConnectionManager 类
  - [ ] connect() - 建立连接
  - [ ] disconnect() - 断开连接
  - [ ] broadcast() - 广播消息
  - [ ] send_personal_message() - 发送个人消息
- [ ] 实现作业进度推送端点
- [ ] 实现系统事件通知端点
- [ ] 实现连接认证
- [ ] 集成到 FastAPI

### 前端部分
- [ ] 创建 `src/hooks/useWebSocket.ts` - WebSocket Hook
  - [ ] 连接管理
  - [ ] 消息处理
  - [ ] 重连逻辑
  - [ ] 错误处理
- [ ] 创建 `src/services/websocket.ts` - WebSocket 服务
- [ ] 集成 Socket.IO 客户端
- [ ] 实现实时进度更新
- [ ] 实现系统通知
- [ ] 实现 Worker 状态实时更新

## 依赖

- Ticket 003: REST API
- Ticket 013: Web 前端框架

## 输出

- 后端 WebSocket 处理器
- 前端 WebSocket Hook
- 实时通信集成

## 验收标准

1. WebSocket 连接稳定
2. 作业进度可以实时推送
3. 系统事件可以实时通知
4. 连接断开后可以自动重连
5. 测试通过

## 参考 ADR

- ADR 0004: REST API 规范 (WebSocket 部分)
- ADR 0006: Worker 通信协议
