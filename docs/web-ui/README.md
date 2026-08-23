# Web UI 开发文档

## 概述

AI-FanYi Web UI 是影视 AI 配音平台的用户界面，提供直观的图形化操作界面，让用户无需了解底层技术细节即可完成视频配音任务。

## 架构

```
┌─────────────────────────────────────────────┐
│                 前端层                      │
│         React + TypeScript + Vite           │
│   TanStack Query + Zustand + React Router  │
└──────────────────────┬──────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────┐
│              Web Backend 层                 │
│              FastAPI + WebSocket            │
└──────────────────────┬──────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────┐
│                 Layer 0                      │
│   Workflow / Selector / Scheduler / State   │
└──────────────────────┬──────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────┐
│                执行层 (M01-M14)              │
└─────────────────────────────────────────────┘
```

## 快速开始

### 使用 Docker Compose（推荐）

```bash
# 启动所有服务
./scripts/start-web-ui.sh

# 访问
# 前端: http://localhost:3000
# 后端 API: http://localhost:8001/api/v1/docs
# 健康检查: http://localhost:8001/api/v1/health
```

### 开发模式

#### 后端开发

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动后端
uvicorn filmdub.apps.web.backend.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端开发

```bash
cd src/filmdub/apps/web/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 项目结构

```
src/filmdub/apps/web/
├── backend/                    # Web Backend
│   ├── main.py                # FastAPI 应用入口
│   ├── api/                   # API 路由
│   │   ├── health.py          # 健康检查
│   │   ├── auth.py            # 认证 (TODO: ticket 02)
│   │   ├── projects.py        # 项目管理 (TODO: ticket 03)
│   │   ├── jobs.py            # 任务管理 (TODO: ticket 05)
│   │   ├── uploads.py         # 文件上传 (TODO: ticket 04)
│   │   ├── characters.py      # 人物数据库 (TODO: ticket 08)
│   │   └── system.py          # 系统状态 (TODO: ticket 12)
│   ├── websocket/             # WebSocket
│   │   └── events.py          # 事件推送 (TODO: ticket 06)
│   ├── services/              # 业务逻辑层
│   ├── models/                # 数据库模型
│   │   └── __init__.py        # User 模型
│   └── tests/                 # 测试
└── frontend/                   # React 前端
    ├── src/
    │   ├── components/        # 组件
    │   │   ├── ui/           # UI 组件
    │   │   └── layout/       # 布局组件
    │   ├── pages/            # 页面
    │   ├── hooks/            # 自定义 Hooks
    │   ├── services/         # API 服务
    │   ├── store/            # 状态管理
    │   ├── types/            # TypeScript 类型
    │   ├── utils/            # 工具函数
    │   └── App.tsx           # 应用入口
    ├── package.json
    └── vite.config.ts
```

## 环境变量

### 后端 (.env)

```bash
# 数据库
DATABASE_URL=postgresql://filmdubbing:filmdubbing_password@localhost:5432/filmdubbing

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_USE_HTTPS=0

# 应用配置
ENVIRONMENT=development
DEBUG=1
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-change-in-production

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

### 前端 (.env)

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## 数据库迁移

```bash
# 创建新迁移
alembic revision --autogenerate -m "migration description"

# 升级到最新版本
alembic upgrade head

# 降级一个版本
alembic downgrade -1

# 查看迁移历史
alembic history

# 查看当前版本
alembic current
```

## 测试

### 后端测试

```bash
# 运行所有测试
pytest src/filmdub/apps/web/backend/tests/

# 运行特定测试文件
pytest src/filmdub/apps/web/backend/tests/test_health.py

# 查看覆盖率
pytest --cov=src/filmdub/apps/web/backend src/filmdub/apps/web/backend/tests/
```

### 前端测试

```bash
cd src/filmdub/apps/web/frontend

# 运行单元测试
npm test

# 运行测试并监听变化
npm test -- --watch

# 查看覆盖率
npm test -- --coverage

# 运行 E2E 测试
npm run test:e2e
```

## API 文档

启动后端后，访问以下地址查看自动生成的 API 文档：

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Tickets 进度

- [x] 01 - Web UI 基础设施搭建
- [ ] 02 - 用户认证系统
- [ ] 03 - 项目管理 UI
- [ ] 04 - 视频文件上传
- [ ] 05 - 任务创建与管理
- [ ] 06 - WebSocket 实时事件推送
- [ ] 07 - 仪表盘（Dashboard）页面
- [ ] 08 - 人物数据库 UI
- [ ] 09 - 输出视频播放与下载
- [ ] 10 - 错误处理与用户反馈
- [ ] 11 - 用户设置页面
- [ ] 12 - 系统状态页面（管理员）
- [ ] 13 - E2E 测试
- [ ] 14 - 文档编写与部署配置

详细的 tickets 信息请参考：`.scratch/web-ui-tickets/README.md`

## 常见问题

### 1. 后端启动失败，提示数据库连接错误

确保 PostgreSQL 容器正在运行：
```bash
docker-compose ps postgres
docker-compose logs postgres
```

### 2. 前端无法连接到后端

检查：
- 后端是否正在运行
- 环境变量 `VITE_API_BASE_URL` 是否正确
- CORS 配置是否包含前端地址

### 3. WebSocket 连接失败

检查：
- JWT Token 是否有效
- WebSocket 端点是否正确：`/api/v1/ws/jobs?token={jwt_token}`

### 4. 数据库迁移失败

检查：
- 数据库连接配置
- 迁移文件是否有语法错误
- 手动执行 SQL 语句查看具体错误

## 开发指南

### 添加新的 API 端点

1. 在 `src/filmdub/apps/web/backend/api/` 创建新的路由文件
2. 在 `main.py` 中注册路由
3. 在 `services/` 创建对应的业务逻辑
4. 在 `tests/` 添加测试

### 添加新的页面

1. 在 `src/filmdub/apps/web/frontend/src/pages/` 创建新的页面组件
2. 在 `App.tsx` 中添加路由
3. 在 `Layout.tsx` 中添加导航链接（如需要）

### 添加新的 UI 组件

1. 在 `src/filmdub/apps/web/frontend/src/components/ui/` 创建新组件
2. 使用现有的 UI 组件作为参考
3. 保持组件的可复用性和可定制性

## 贡献指南

1. 遵循现有的代码风格
2. 为新功能添加测试
3. 更新相关文档
4. 提交前运行所有测试
5. 使用有意义的 commit 消息

## 许可证

MIT License
