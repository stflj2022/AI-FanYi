# 01: Web UI 基础设施搭建

**What to build:**
建立 Web UI 的完整技术栈基础，包括前端项目脚手架、后端 FastAPI 应用、数据库模型扩展、Docker 配置，以及基本的开发环境。完成后可以运行前端和后端服务，并通过健康检查接口验证。

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] 创建 React + TypeScript + Vite 前端项目脚手架
- [ ] 配置 shadcn/ui 组件库
- [ ] 配置前端状态管理（TanStack Query + Zustand）
- [ ] 配置前端路由（React Router v6）
- [ ] 创建 Web Backend FastAPI 应用结构
- [ ] 添加 User 模型到数据库
- [ ] 扩展 ProjectRecord 模型（添加 owner_id, cover_image_url）
- [ ] 扩展 Job 模型（添加 user_friendly_status, user_friendly_error）
- [ ] 扩展 Character 模型（添加 avatar_url, first_appearance_episode_name）
- [ ] 编写数据库迁移脚本（Alembic）
- [ ] 配置 Web Backend 的数据库和 Redis 连接
- [ ] 创建 Dockerfile 和 docker-compose 配置
- [ ] 添加健康检查 API 端点（GET /health）
- [ ] 配置前端环境变量和 API 基础 URL
- [ ] 编写基础测试（后端健康检查、前端渲染）
