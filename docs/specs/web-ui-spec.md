# Web UI 规范文档

**创建日期**: 2026-03-23
**状态**: Draft
**相关计划**: `/home/wu/桌面/AI-FanYi/计划书/ai-fanyi-web ui.txt`

---

## Problem Statement

当前 AI-FanYi 平台是一个功能完整的影视 AI 配音生产系统，包含 Layer 0 编排层和 14 个核心模块（M01-M14）。然而，用户只能通过命令行或直接调用 API 来使用这些功能，缺乏一个直观的图形化界面。

用户面临的问题：
1. **学习成本高**: 需要理解 Layer 0 和 14 个模块的概念才能使用平台
2. **操作复杂**: 需要手动管理项目、作业、 artifacts 等概念
3. **缺乏实时反馈**: 无法直观地查看任务进度和系统状态
4. **不便于非技术人员使用**: 影视后期制作人员可能不熟悉命令行操作

从用户视角看，问题可以简化为：**我想把一部外语影视剧变成中文配音版，但不知道如何操作。**

---

## Solution

构建一个 Web UI，将 Layer 0 + 14 Modules 封装成一个用户只需"上传 → 配音 → 下载"的影视 AI 配音平台。

### 核心原则

1. **极简设计**: 用户永远不需要知道 M01～M14 的存在
2. **三步完成**: 上传视频 → 选择语言 → 开始配音
3. **实时反馈**: 通过 WebSocket 实时显示任务进度
4. **用户友好**: 错误信息不包含工程术语，使用自然语言描述

### 架构概览

```
┌─────────────────────────────────────────────┐
│                 用户层                      │
│                                             │
│             React Web UI                   │
│     输入视频 → 配音任务 → 输出视频          │
└──────────────────────┬──────────────────────┘
                           │
                           ▼
    ┌─────────────────────────────────────────────┐
    │                 控制层                      │
    │                                             │
    │              Web Backend API                │
    │          (FastAPI + WebSocket)              │
    │                                             │
    │   POST /api/projects                       │
    │   POST /api/jobs                           │
    │   WS   /api/ws/jobs/{id}                   │
    └──────────────────────┬──────────────────────┘
                           │
                           ▼
    ┌─────────────────────────────────────────────┐
    │                 Layer 0                     │
    │   Workflow / Selector / Scheduler / State   │
    └──────────────────────┬──────────────────────┘
                           │
                           ▼
    ┌─────────────────────────────────────────────┐
    │                 执行层                      │
    │         M01 → M02 → ... → M14              │
    └─────────────────────────────────────────────┘
```

### 用户界面设计

#### 主页 (Dashboard)

```
┌──────────────────────────────────────────────┐
│ AI影视配音                                  │
├──────────────────────────────────────────────┤
│                                              │
│              ＋                              │
│           添加视频                           │
│                                              │
│      把影视视频拖到这里                      │
│                                              │
├──────────────────────────────────────────────┤
│ 最近任务                                     │
│                                              │
│ Breaking Bad S01E01       ✓ 已完成           │
│ Breaking Bad S01E02       ● 配音中           │
│ Breaking Bad S01E03       ⏸ 已暂停           │
│                                              │
└──────────────────────────────────────────────┘
```

#### 任务详情页

```
┌─────────────────────────────────────────────┐
│ Breaking Bad S01E02                         │
├─────────────────────────────────────────────┤
│                                             │
│ ███████████████████░░  91%                  │
│                                             │
│ 正在生成配音                                │
│                                             │
│ 当前：Jesse Pinkman                         │
│                                             │
│ 已处理 324 / 351 条对白                     │
│                                             │
│ 预计剩余：8 分钟                             │
│                                             │
│ [暂停]                    [取消]             │
│                                             │
└─────────────────────────────────────────────┘
```

---

## User Stories

### 核心功能

1. 作为一名**影视后期制作人员**，我希望能够**上传视频文件**，以便开始配音任务。

2. 作为一名**影视后期制作人员**，我希望能够**选择目标语言**（如中文），以便生成指定语言的配音。

3. 作为一名**影视后期制作人员**，我希望能够**一键开始配音任务**，无需理解底层模块的工作流程。

4. 作为一名**影视后期制作人员**，我希望能够**实时查看任务进度**，包括当前阶段、完成百分比、预计剩余时间。

5. 作为一名**影视后期制作人员**，我希望能够**暂停/恢复任务**，以便在需要时控制任务执行。

6. 作为一名**影视后期制作人员**，我希望能够**取消正在进行的任务**，以便放弃不需要的工作。

7. 作为一名**影视后期制作人员**，我希望能够**在线预览配音后的视频**，以便快速验证结果。

8. 作为一名**影视后期制作人员**，我希望能够**下载配音后的视频**，以便进行后续处理。

### 项目管理

9. 作为一名**用户**，我希望能够**创建新项目**，以便组织不同剧集的配音工作。

10. 作为一名**用户**，我希望能够**查看项目列表**，包括项目状态、进度、创建时间。

11. 作为一名**用户**，我希望能够**删除项目**，以便清理不再需要的工作。

12. 作为一名**用户**，我希望能够**查看项目详情**，包括关联的剧集、人物库、任务历史。

### 任务管理

13. 作为一名**用户**，我希望能够**查看所有任务**，包括任务状态、关联项目、执行时间。

14. 作为一名**用户**，我希望能够**筛选任务**（按状态、项目、时间），以便快速找到需要的任务。

15. 作为一名**用户**，我希望能够**重试失败的任务**，以便恢复因临时问题而失败的工作。

16. 作为一名**用户**，我希望能够**查看任务日志**，以便了解任务执行细节和排查问题。

### 人物数据库

17. 作为一名**用户**，我希望能够**查看项目的人物数据库**，包括人物名称、原声演员、音色状态。

18. 作为一名**用户**，我希望能够**编辑人物信息**，如添加描述、修正人物属性。

19. 作为一名**用户**，我希望能够**管理人物的音色档案**，如选择或重新生成音色。

20. 作为一名**用户**，我希望能够**在不同项目之间复用人物和音色**，以便保持整季/整剧的音色一致性。

### 用户认证

21. 作为一名**用户**，我希望能够**注册账号**，以便使用平台的所有功能。

22. 作为一名**用户**，我希望能够**登录系统**，以便访问我的项目和任务。

23. 作为一名**用户**，我希望能够**修改密码**，以便保证账号安全。

24. 作为一名**管理员**，我希望能够**管理用户**，如创建、禁用用户。

### 错误处理

25. 作为一名**用户**，我希望能够**看到用户友好的错误消息**，而不是工程术语和堆栈跟踪。

26. 作为一名**用户**，我希望能够**在任务失败时继续处理已完成部分**，以便不浪费已完成的工作。

27. 作为一名**用户**，我希望能够**查看详细的错误日志**（可选），以便向技术支持报告问题。

28. 作为一名**用户**，我希望能够**收到任务完成或失败的通知**，以便及时了解任务状态。

### 系统设置

29. 作为一名**用户**，我希望能够**配置默认目标语言**，以便快速开始任务。

30. 作为一名**用户**，我希望能够**配置默认质量设置**（快速/标准/高质量）。

31. 作为一名**用户**，我希望能够**配置高级选项**（如工作流类型、字幕源、失败策略），以便进行精细控制。

32. 作为一名**管理员**，我希望能够**查看系统状态**，包括 GPU 使用率、队列长度、Worker 状态。

### 文件管理

33. 作为一名**用户**，我希望能够**上传大文件**（多个 GB），并查看上传进度。

34. 作为一名**用户**，我希望能够**断点续传**，以便在网络中断后继续上传。

35. 作为一名**用户**，我希望能够**查看已上传文件**的元数据（时长、分辨率、编码格式）。

### 翻译记忆

36. 作为一名**用户**，我希望能够**查看翻译记忆**，如特定人物的常用译法。

37. 作为一名**用户**，我希望能够**修改翻译**，以便纠正不准确的翻译。

38. 作为一名**用户**，我希望能够**查看翻译使用上下文**（如首次出现的剧集），以便理解翻译的适用场景。

### 导出与分享

39. 作为一名**用户**，我希望能够**导出配音配置**，以便在其他项目中复用。

40. 作为一名**用户**，我希望能够**生成任务报告**，包括处理时间、资源使用、质量指标。

---

## Implementation Decisions

### 技术栈

#### 前端
- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **UI 组件库**: shadcn/ui (基于 Radix UI)
- **状态管理**:
  - 服务器状态: TanStack Query (React Query)
  - 客户端 UI 状态: Zustand
- **表单处理**: React Hook Form
- **路由**: React Router v6
- **HTTP 客户端**: axios (底层) + TanStack Query
- **文件上传**: react-dropzone (第一版) → uppy (第二版)
- **视频播放**: HTML5 `<video>` + Plyr
- **WebSocket**: 原生 WebSocket API
- **测试**: Vitest + React Testing Library + Playwright (E2E)

#### 后端
- **框架**: FastAPI (Python 3.11+)
- **WebSocket**: FastAPI 原生 WebSocket
- **数据库**:
  - PostgreSQL (已有)
  - 新增 User 模型
  - 扩展现有 ProjectRecord、Job、Character、VoiceProfile 模型
- **缓存**: Redis (已有)
- **对象存储**: MinIO (已有)
- **认证**: JWT (已有配置)
- **测试**: pytest + FastAPI TestClient + pytest-asyncio

### 架构决策

#### 1. Web Backend 与 Layer 0 的关系

**决策**: Web Backend 作为独立的 FastAPI 应用，但**直接导入和调用** Layer 0 的 Python 代码（共享模型、服务、工作流），不走 HTTP。

**理由**:
- 避免网络开销和序列化/反序列化成本
- 保持代码单一真理来源
- 简化部署和维护

**实现**:
```
web/
├── backend/
│   ├── main.py              # FastAPI 应用入口
│   ├── api/                 # API 路由
│   │   ├── auth.py
│   │   ├── projects.py
│   │   ├── jobs.py
│   │   ├── uploads.py
│   │   ├── characters.py
│   │   └── system.py
│   ├── websocket/           # WebSocket 路由
│   │   └── events.py
│   ├── services/            # 业务逻辑层
│   │   ├── auth_service.py
│   │   ├── project_service.py
│   │   ├── job_service.py
│   │   └── character_service.py
│   ├── models/              # 数据库模型（扩展 Layer 0）
│   │   └── user.py
│   └── dependencies.py      # 依赖注入
└── frontend/                # React 前端
```

#### 2. 部署方式

**决策**: Web Backend 作为单独的容器，但与 Layer 0 API 共享网络卷（可以直接访问数据库、Redis）。

**理由**:
- 独立部署，互不影响
- 共享数据层，保持一致性
- 便于扩展和负载均衡

**Docker Compose 配置**:
```yaml
services:
  web-backend:
    build:
      context: .
      dockerfile: docker/Dockerfile.web
    ports:
      - "8001:8000"  # Web Backend 端口
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
      - MINIO_ENDPOINT=minio:9000
    volumes:
      - ./src:/app/src  # 共享 Layer 0 代码
    depends_on:
      - postgres
      - redis
      - minio
```

#### 3. 文件上传策略

**第一版（快速上线）**:
- 前端直接上传到后端（`POST /api/uploads`）
- 后端保存到临时目录，然后上传到 MinIO
- 不支持断点续传

**第二版（性能优化）**:
- 使用 MinIO 预签名 URL
- 浏览器直接上传到 MinIO（减少后端压力）
- 使用 MinIO multipart upload API 实现断点续传
- 前端使用 uppy 库管理上传

#### 4. WebSocket 实时通信

**决策**: 使用 FastAPI 原生 WebSocket，每个用户一个连接，使用 job_id 进行多路复用。

**事件格式**:
```json
{
  "event_type": "job.progress" | "job.stage" | "job.error" | "job.completed",
  "job_id": "uuid",
  "timestamp": "2026-03-23T10:00:00Z",
  "data": {
    "progress": 0.72,
    "stage": "voice_generation",
    "stage_name": "正在生成人物对白",
    "message": "正在生成第 183 条对白...",
    "current_character": "Jesse Pinkman",
    "processed_count": 183,
    "total_count": 271,
    "estimated_remaining_seconds": 480
  }
}
```

**连接管理**:
```python
# 前端连接
const ws = new WebSocket(`ws://localhost:8000/api/ws/jobs?token=${jwtToken}`);

# 发送订阅请求
ws.send(JSON.stringify({
  action: "subscribe",
  job_ids: ["job-uuid-1", "job-uuid-2"]
}));

# 接收事件
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // 根据 event_type 处理不同事件
};
```

#### 5. 错误映射策略

**决策**: 在 Web Backend 做映射层。Layer 0 返回结构化错误，Web Backend 将错误码映射为用户友好的消息。

**Layer 0 错误格式**:
```json
{
  "code": "M09_AUDIO_MIX_FAILED",
  "message": "Audio mixing failed: FFmpeg exited with code 1",
  "details": {
    "module": "M09",
    "exit_code": 1,
    "stderr": "..."
  }
}
```

**Web Backend 错误映射**:
```python
ERROR_MESSAGES = {
    "M09_AUDIO_MIX_FAILED": {
        "user_message": "音频合成暂时遇到问题，系统正在自动重试。",
        "severity": "warning",
        "action": "retry"
    },
    "M07_TRANSLATION_ERROR": {
        "user_message": "翻译服务暂时不可用，请稍后重试。",
        "severity": "error",
        "action": "manual"
    }
}
```

**错误日志**:
- 数据库：存错误摘要（code, user_message, severity）
- 文件系统：存详细日志（按 `logs/jobs/{job_id}/` 组织）

#### 6. 用户认证与授权

**决策**: 使用 JWT Token 认证，两级权限（管理员/普通用户）。

**User 模型**:
```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
```

**Project 扩展**:
```python
# 在 ProjectRecord 模型中添加
owner_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
```

**权限规则**:
- 普通用户：只能访问自己的项目和任务
- 管理员：可以访问所有项目，查看系统状态

#### 7. 数据库模型扩展

**新增 User 模型**（见上文）

**扩展 ProjectRecord 模型**:
```python
# 新增字段
owner_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), nullable=False)
cover_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
```

**扩展 Job 模型**:
```python
# 新增字段
user_friendly_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
user_friendly_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

**扩展 Character 模型**:
```python
# 新增字段
avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
first_appearance_episode_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
```

**新增 TranslationMemory 模型**（第二版）:
```python
class TranslationMemory(Base):
    __tablename__ = "translation_memory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("characters.id"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("projects.id"), nullable=False)

    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    first_appearance_season: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    first_appearance_episode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

#### 8. API 设计

**REST API 端点**:

```
# 认证
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout

# 项目
GET    /api/v1/projects
POST   /api/v1/projects
GET    /api/v1/projects/{id}
PUT    /api/v1/projects/{id}
DELETE /api/v1/projects/{id}
GET    /api/v1/projects/{id}/characters

# 任务
GET    /api/v1/jobs
POST   /api/v1/jobs
GET    /api/v1/jobs/{id}
POST   /api/v1/jobs/{id}/pause
POST   /api/v1/jobs/{id}/resume
POST   /api/v1/jobs/{id}/cancel
POST   /api/v1/jobs/{id}/retry
GET    /api/v1/jobs/{id}/events
GET    /api/v1/jobs/{id}/output
GET    /api/v1/jobs/{id}/logs

# 文件上传
POST   /api/v1/uploads
GET    /api/v1/uploads/{id}
POST   /api/v1/uploads/{id}/chunks  # 第二版

# 人物数据库
GET    /api/v1/characters
GET    /api/v1/characters/{id}
PUT    /api/v1/characters/{id}
GET    /api/v1/characters/{id}/voice-profiles

# 翻译记忆（第二版）
GET    /api/v1/translation-memory
GET    /api/v1/translation-memory/{id}
PUT    /api/v1/translation-memory/{id}

# 系统状态（仅管理员）
GET    /api/v1/system/status
GET    /api/v1/system/workers
GET    /api/v1/system/queue

# WebSocket
WS     /api/v1/ws/jobs?token={jwt_token}
```

**WebSocket 协议**:

客户端 → 服务器:
```json
{
  "action": "subscribe" | "unsubscribe",
  "job_ids": ["uuid-1", "uuid-2"]
}
```

服务器 → 客户端:
```json
{
  "event_type": "job.progress" | "job.stage" | "job.error" | "job.completed",
  "job_id": "uuid",
  "timestamp": "ISO8601",
  "data": { ... }
}
```

#### 9. 前端状态管理

**TanStack Query (服务器状态)**:
```typescript
// 查询项目列表
const { data: projects, isLoading } = useQuery({
  queryKey: ['projects'],
  queryFn: () => api.getProjects()
});

// 创建项目
const createProjectMutation = useMutation({
  mutationFn: (data) => api.createProject(data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['projects'] });
  }
});

// 订阅任务更新
const { data: jobStatus } = useQuery({
  queryKey: ['jobs', jobId],
  queryFn: () => api.getJob(jobId),
  refetchInterval: 5000  // 轮询备份
});
```

**Zustand (客户端 UI 状态)**:
```typescript
interface AppState {
  currentProjectId: string | null;
  setCurrentProjectId: (id: string | null) => void;
  selectedJobIds: string[];
  toggleJobSelection: (id: string) => void;
}

const useAppStore = create<AppState>((set) => ({
  currentProjectId: null,
  setCurrentProjectId: (id) => set({ currentProjectId: id }),
  selectedJobIds: [],
  toggleJobSelection: (id) => set((state) => ({
    selectedJobIds: state.selectedJobIds.includes(id)
      ? state.selectedJobIds.filter((x) => x !== id)
      : [...state.selectedJobIds, id]
  }))
}));
```

#### 10. 前端路由设计

```typescript
const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "projects", element: <ProjectList /> },
      { path: "projects/new", element: <ProjectCreate /> },
      { path: "projects/:id", element: <ProjectDetail /> },
      { path: "jobs", element: <JobList /> },
      { path: "jobs/:id", element: <JobDetail /> },
      { path: "characters", element: <CharacterList /> },
      { path: "characters/:id", element: <CharacterDetail /> },
      { path: "settings", element: <Settings /> },
      { path: "system", element: <SystemStatus />, element: <AdminRoute><SystemStatus /></AdminRoute> }
    ]
  },
  { path: "/login", element: <Login /> },
  { path: "/register", element: <Register /> }
]);
```

#### 11. 视频播放方案

**第一版**:
- 使用 HTML5 `<video>` 标签
- 使用 MinIO 预签名 URL 直接播放
- 使用 Plyr 提供美观的 UI
- 不转码，假设输出格式浏览器支持（MP4/H.264/AAC）

**第二版**:
- 支持 HLS 流媒体（使用 hls.js）
- 后端自动转码为兼容格式
- 支持多码率自适应

---

## Testing Decisions

### 前端测试

**单元测试** (Vitest + React Testing Library):
- 测试组件的渲染和用户交互
- 测试表单验证和提交
- 测试状态管理逻辑

**E2E 测试** (Playwright):
- 测试核心用户流程：
  1. 用户注册/登录
  2. 创建项目
  3. 上传视频
  4. 创建配音任务
  5. 等待任务完成（模拟）
  6. 播放配音视频
  7. 下载视频

### 后端测试

**单元测试** (pytest):
- 测试 API endpoints 的输入输出
- 测试服务层的业务逻辑
- 测试错误映射

**集成测试** (pytest + TestClient):
- 测试完整的请求-响应周期
- 测试 WebSocket 连接和事件推送
- 测试文件上传流程

### 测试原则

1. **只测试外部行为**: 不测试实现细节
2. **最高 seam 测试**: 优先测试 API 层和组件层
3. **覆盖核心流程**: 重点测试用户可见的功能
4. **快速反馈**: 单元测试应该很快，E2E 测试可以慢但数量少

---

## Out of Scope

### 第一版不包含的功能

1. **翻译记忆 UI**: 翻译记忆功能后端会实现，但第一版不提供 UI
2. **系统状态页面**: 管理员可以查看系统状态，但第一版不提供详细 UI
3. **断点续传**: 大文件上传暂不支持断点续传
4. **HLS 流媒体**: 视频播放不使用流媒体技术
5. **OAuth 认证**: 只支持用户名/密码登录
6. **多语言 UI**: UI 只支持中文
7. **批量处理**: 第一版只支持单集处理
8. **高级工作流配置**: 用户无法自定义工作流，只能选择预设质量
9. **任务报告**: 不生成详细的任务报告
10. **导出/导入配置**: 不支持配置的导出和导入

### 可能的第二版功能

1. 翻译记忆 UI（查看、修改、使用上下文）
2. 系统状态页面（GPU、CPU、内存、队列）
3. 断点续传（大文件上传）
4. HLS 流媒体（支持大文件播放）
5. OAuth 认证（Google、GitHub 登录）
6. 多语言 UI（支持英文）
7. 批量处理（整季/整剧处理）
8. 高级工作流配置（自定义模块顺序）
9. 任务报告（处理时间、资源使用、质量指标）
10. 配置导出/导入（复用配音配置）

---

## Further Notes

### 与 Layer 0 的集成

Web UI 必须**严格遵循** Layer 0 的以下契约：

1. **状态机**: 使用 Layer 0 定义的 JobStatus 和 ProjectStatus
2. **Artifact 管理**: 通过 Layer 0 的 Artifact Registry 获取和存储文件
3. **工作流调度**: 通过 Layer 0 的 Workflow Selector 选择合适的工作流
4. **错误处理**: 遵循 Layer 0 的错误码和恢复策略

### 性能考虑

1. **前端优化**:
   - 使用 React.lazy 和 Suspense 进行代码分割
   - 使用 TanStack Query 的缓存和去重
   - 虚拟滚动处理长列表

2. **后端优化**:
   - 使用 Redis 缓存频繁查询的数据
   - 使用数据库索引加速查询
   - 使用 WebSocket 减少轮询

3. **文件传输**:
   - 使用 MinIO 预签名 URL
   - 启用 gzip 压缩
   - 使用 CDN（可选）

### 安全考虑

1. **认证**:
   - JWT Token 过期时间：24 小时
   - Refresh Token 过期时间：30 天
   - 密码使用 bcrypt 哈希

2. **授权**:
   - 项目级别的数据隔离
   - API 端点的权限检查
   - 管理员操作的审计日志

3. **文件安全**:
   - 上传文件大小限制：10 GB
   - 文件类型白名单验证
   - MinIO 访问权限控制

### 可维护性

1. **代码组织**:
   - 按功能模块组织代码（projects、jobs、characters）
   - 共享逻辑提取到独立的模块
   - 统一的错误处理和日志记录

2. **文档**:
   - API 文档（使用 FastAPI 自动生成）
   - 组件文档（使用 Storybook，可选）
   - 部署文档

3. **监控**:
   - 前端错误上报（Sentry，可选）
   - 后端日志聚合
   - 性能监控

### 开发流程

按照 Matt Skills 工作流：

1. **grill-with-docs**: 设计质询，澄清设计细节 ✅ (已完成)
2. **to-spec**: 生成规范文档 ✅ (本文档)
3. **to-tickets**: 分解为任务 tickets
4. **implement**: 执行实现
5. **code-review**: 双轴代码审查
6. **E2E 测试**: 端到端测试验证

### 与现有代码的兼容性

1. **数据库迁移**:
   - 使用 Alembic 管理数据库迁移
   - 扩展现有模型，不破坏现有数据

2. **API 兼容性**:
   - Web Backend 不修改 Layer 0 API
   - 新增的 API 端点使用 `/api/v1` 前缀

3. **Docker Compose**:
   - 在现有 `docker-compose.yml` 中添加 Web Backend 服务
   - 共享现有的网络和卷

---

**文档结束**
