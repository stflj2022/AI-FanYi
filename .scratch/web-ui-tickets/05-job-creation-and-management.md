# 05: 任务创建与管理

**What to build:**
实现配音任务的创建、列表、详情、暂停、恢复、取消、重试功能。用户可以基于上传的视频创建配音任务，查看所有任务列表，查看任务详情，以及控制任务的执行。

**Blocked by:** 01-web-ui-foundation, 02-user-authentication, 03-project-management-ui, 04-video-upload

**Status:** ready-for-agent

- [ ] 创建 Job Service
- [ ] 实现创建任务 API（POST /api/v1/jobs）
- [ ] 实现获取任务列表 API（GET /api/v1/jobs，支持筛选和分页）
- [ ] 实现获取任务详情 API（GET /api/v1/jobs/{id}）
- [ ] 实现暂停任务 API（POST /api/v1/jobs/{id}/pause）
- [ ] 实现恢复任务 API（POST /api/v1/jobs/{id}/resume）
- [ ] 实现取消任务 API（POST /api/v1/jobs/{id}/cancel）
- [ ] 实现重试任务 API（POST /api/v1/jobs/{id}/retry）
- [ ] 集成 Layer 0 的 Workflow Selector（选择合适的工作流）
- [ ] 实现任务状态同步（从 Layer 0 获取状态）
- [ ] 创建任务列表页面（JobList 组件）
- [ ] 创建任务详情页面（JobDetail 组件）
- [ ] 创建任务卡片组件（JobCard）
- [ ] 创建任务控制按钮（暂停、恢复、取消、重试）
- [ ] 实现任务状态标签（pending, running, completed, failed）
- [ ] 实现任务筛选（按状态、项目、时间）
- [ ] 实现前端任务查询和管理
- [ ] 编写任务管理相关测试
