# 12: 系统状态页面（管理员）

**What to build:**
实现系统状态监控页面，仅管理员可见。显示 GPU 使用率、CPU 使用率、内存使用量、Worker 状态、队列长度、以及 Layer 0 各模块的状态。

**Blocked by:** 01-web-ui-foundation, 02-user-authentication

**Status:** ready-for-agent

- [ ] 实现获取系统状态 API（GET /api/v1/system/status）
- [ ] 实现获取 Worker 状态 API（GET /api/v1/system/workers）
- [ ] 实现获取队列状态 API（GET /api/v1/system/queue）
- [ ] 实现管理员权限检查
- [ ] 集成系统监控数据（CPU、内存、GPU）
- [ ] 创建系统状态页面布局（SystemStatus 组件）
- [ ] 创建系统资源卡片（CPU、内存、GPU、存储）
- [ ] 创建 Worker 状态列表
- [ ] 创建队列状态显示
- [ ] 创建 Layer 0 模块状态监控
- [ ] 实现实时数据刷新（WebSocket 或轮询）
- [ ] 实现管理员路由保护
- [ ] 优化数据可视化（使用图表库，可选）
- [ ] 编写系统状态相关测试
