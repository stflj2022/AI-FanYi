# 07: 仪表盘（Dashboard）页面

**What to build:**
实现主页仪表盘，显示快速操作入口（添加视频）和最近任务列表。用户登录后首先看到这个页面，可以快速开始新的配音任务，或查看最近的任务状态。

**Blocked by:** 01-web-ui-foundation, 02-user-authentication, 05-job-creation-and-management, 06-websocket-realtime-events

**Status:** ready-for-agent

- [ ] 实现获取最近任务 API（GET /api/v1/jobs/recent）
- [ ] 实现获取统计数据 API（总任务数、运行中、已完成等）
- [ ] 创建 Dashboard 页面布局
- [ ] 创建快速操作卡片（添加视频、创建项目）
- [ ] 创建任务统计卡片（总数、运行中、已完成、失败）
- [ ] 创建最近任务列表组件
- [ ] 实现任务状态的实时更新（WebSocket）
- [ ] 创建任务快捷操作（从 Dashboard 跳转到任务详情）
- [ ] 实现空状态提示（没有任务时显示引导）
- [ ] 优化 Dashboard 响应式布局
- [ ] 编写 Dashboard 相关测试
