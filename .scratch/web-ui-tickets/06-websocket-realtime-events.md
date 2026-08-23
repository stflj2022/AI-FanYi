# 06: WebSocket 实时事件推送

**What to build:**
实现 WebSocket 连接和实时事件推送，让用户可以实时看到任务进度、阶段变化、错误信息和完成通知。前端订阅任务事件后，无需轮询即可接收实时更新。

**Blocked by:** 01-web-ui-foundation, 02-user-authentication, 05-job-creation-and-management

**Status:** ready-for-agent

- [ ] 创建 WebSocket 路由（/api/v1/ws/jobs）
- [ ] 实现 WebSocket 连接管理（连接池、心跳检测）
- [ ] 实现 JWT Token 验证（连接时验证）
- [ ] 实现订阅/取消订阅机制（按 job_id）
- [ ] 定义事件格式（job.progress, job.stage, job.error, job.completed）
- [ ] 实现事件广播（发送给订阅的客户端）
- [ ] 从 Layer 0 接收事件并转发
- [ ] 创建前端 WebSocket Hook（useWebSocket）
- [ ] 实现自动重连机制
- [ ] 实现事件订阅管理
- [ ] 创建进度条组件（实时更新进度）
- [ ] 创建当前阶段显示组件
- [ ] 创建错误通知组件（Toast）
- [ ] 实现任务完成通知（浏览器 Notification）
- [ ] 优化事件节流和防抖
- [ ] 编写 WebSocket 相关测试（包括连接断开重连）
