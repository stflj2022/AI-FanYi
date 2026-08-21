# Ticket 003: REST API - 项目和作业管理

## 状态: done（第3轮复验通过：项目/作业 CRUD+生命周期全绿，补充 Artifacts API（上传/下载/列表/删除）、PUT 别名、真实存储后端选择，含 31 个 API 测试）

## 优先级: 高

## 模块: Layer 0 Orchestrator

## 描述

实现项目和作业管理的 REST API 端点，支持项目的 CRUD 操作和作业的生命周期管理。

## 任务清单

- [ ] 创建 `src/filmdub/apps/api/main.py` - FastAPI 应用入口
- [ ] 创建 `src/filmdub/apps/api/dependencies.py` - 依赖注入
- [ ] 创建 `src/filmdub/apps/api/middleware.py` - 中间件
  - [ ] 认证中间件
  - [ ] 日志中间件
  - [ ] 错误处理中间件
- [ ] 创建 `src/filmdub/apps/api/routers/projects.py` - 项目 API
  - [ ] POST /api/v1/projects - 创建项目
  - [ ] GET /api/v1/projects - 获取项目列表
  - [ ] GET /api/v1/projects/{project_id} - 获取项目详情
  - [ ] PATCH /api/v1/projects/{project_id} - 更新项目
  - [ ] DELETE /api/v1/projects/{project_id} - 删除项目
- [ ] 创建 `src/filmdub/apps/api/routers/jobs.py` - 作业 API
  - [ ] POST /api/v1/projects/{project_id}/jobs - 创建作业
  - [ ] GET /api/v1/projects/{project_id}/jobs - 获取作业列表
  - [ ] GET /api/v1/jobs/{job_id} - 获取作业详情
  - [ ] POST /api/v1/jobs/{job_id}/cancel - 取消作业
  - [ ] POST /api/v1/jobs/{job_id}/retry - 重试作业
- [ ] 实现 Pydantic 模型用于请求/响应验证
- [ ] 实现统一的响应格式
- [ ] 实现错误处理和错误代码
- [ ] 编写 API 测试（使用 pytest + httpx）
- [ ] 编写 API 文档（FastAPI 自动生成）

## 依赖

- Ticket 001: 数据库模型
- Ticket 002: Artifact Registry

## 输出

- 完整的项目和作业 API
- Pydantic 模型
- API 测试
- API 文档

## 验收标准

1. 所有端点按规范实现
2. 请求/响应验证正确
3. 错误处理符合规范
4. API 文档完整
5. 测试覆盖率 > 80%

## 参考 ADR

- ADR 0004: REST API 规范
