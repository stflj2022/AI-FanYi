# 03: 项目管理 UI

**What to build:**
实现项目的创建、列表、详情、删除功能，包括前端页面和后端 API。用户可以创建新的配音项目，查看所有项目列表，查看项目详情（包括关联的人物），以及删除不需要的项目。

**Blocked by:** 01-web-ui-foundation, 02-user-authentication

**Status:** ready-for-agent

- [ ] 创建 Project Service（业务逻辑层）
- [ ] 实现创建项目 API（POST /api/v1/projects）
- [ ] 实现获取项目列表 API（GET /api/v1/projects，支持分页和筛选）
- [ ] 实现获取项目详情 API（GET /api/v1/projects/{id}）
- [ ] 实现更新项目 API（PUT /api/v1/projects/{id}）
- [ ] 实现删除项目 API（DELETE /api/v1/projects/{id}）
- [ ] 实现项目权限检查（用户只能访问自己的项目）
- [ ] 创建项目列表页面（ProjectList 组件）
- [ ] 创建项目创建页面（ProjectCreate 组件，包含表单）
- [ ] 创建项目详情页面（ProjectDetail 组件）
- [ ] 实现项目卡片组件（ProjectCard）
- [ ] 实现项目表单验证（React Hook Form）
- [ ] 实现前端项目查询（TanStack Query）
- [ ] 实现项目删除确认对话框
- [ ] 实现项目列表的筛选和排序
- [ ] 编写项目管理相关测试
