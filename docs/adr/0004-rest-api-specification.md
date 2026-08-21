# ADR 0004: Layer 0 REST API 规范

## 状态

设计中

## 上下文

Layer 0 需要提供 REST API 用于：
1. Web UI 交互
2. Worker 注册和心跳
3. 项目和作业管理
4. Artifact 操作
5. 实时状态监控

## API 设计原则

1. **RESTful**: 遵循 REST 设计原则
2. **版本化**: 通过 URL 路径版本化 (`/api/v1/`)
3. **统一响应格式**: 统一的 JSON 响应结构
4. **错误处理**: 统一的错误代码和消息
5. **认证授权**: JWT Token 认证
6. **限流**: 基于 IP 和用户的限流

## 统一响应格式

### 成功响应

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "uuid"
  }
}
```

### 错误响应

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": { ... }
  },
  "meta": {
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "uuid"
  }
}
```

### 分页响应

```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  },
  "meta": { ... }
}
```

## API 端点

### 1. 项目管理

#### 创建项目

```http
POST /api/v1/projects
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Breaking Bad Season 1",
  "description": "Breaking Bad S01 中文配音",
  "media_type": "tv_series",
  "title": "绝命毒师",
  "title_en": "Breaking Bad",
  "season": 1,
  "original_language": "en",
  "target_language": "zh-CN",
  "tmdb_id": 1396,
  "workflow_id": "uuid"
}

Response 201:
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Breaking Bad Season 1",
    "status": "pending",
    ...
  }
}
```

#### 获取项目列表

```http
GET /api/v1/projects?page=1&page_size=20&status=processing
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "Breaking Bad Season 1",
      "status": "processing",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": { ... }
}
```

#### 获取项目详情

```http
GET /api/v1/projects/{project_id}
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Breaking Bad Season 1",
    "status": "processing",
    "metadata": { ... },
    "statistics": {
      "total_jobs": 14,
      "completed_jobs": 5,
      "failed_jobs": 0
    }
  }
}
```

#### 更新项目

```http
PATCH /api/v1/projects/{project_id}
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "New Name",
  "description": "Updated description"
}

Response 200:
{
  "success": true,
  "data": { ... }
}
```

#### 删除项目

```http
DELETE /api/v1/projects/{project_id}
Authorization: Bearer <token>

Response 204: No Content
```

### 2. 作业管理

#### 创建作业

```http
POST /api/v1/projects/{project_id}/jobs
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "E01 - Pilot",
  "module_id": "M01",
  "depends_on": [],
  "config": { ... }
}

Response 201:
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "E01 - Pilot",
    "status": "pending",
    ...
  }
}
```

#### 获取作业列表

```http
GET /api/v1/projects/{project_id}/jobs?status=running
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": [ ... ]
}
```

#### 获取作业详情

```http
GET /api/v1/jobs/{job_id}
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "E01 - Pilot",
    "status": "running",
    "module_id": "M01",
    "worker_id": "uuid",
    "started_at": "2024-01-01T00:00:00Z",
    "progress": 45,
    "input_artifacts": [ ... ],
    "output_artifacts": [ ]
  }
}
```

#### 取消作业

```http
POST /api/v1/jobs/{job_id}/cancel
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "cancelled"
  }
}
```

#### 重试作业

```http
POST /api/v1/jobs/{job_id}/retry
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "pending",
    "retry_count": 1
  }
}
```

### 3. Worker 管理

#### Worker 注册

```http
POST /api/v1/workers/register
Content-Type: application/json

{
  "name": "worker-gpu-01",
  "type": "gpu",
  "capabilities": {
    "modules": ["M05", "M06", "M09"],
    "gpu": true,
    "gpu_memory_gb": 16
  },
  "cpu_cores": 8,
  "memory_gb": 32,
  "gpu_count": 1,
  "gpu_memory_gb": 16
}

Response 200:
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "worker-gpu-01",
    "status": "idle",
    "worker_token": "jwt_token_for_heartbeat"
  }
}
```

#### Worker 心跳

```http
POST /api/v1/workers/{worker_id}/heartbeat
Content-Type: application/json
Authorization: Bearer <worker_token>

{
  "status": "busy",
  "current_job_id": "uuid",
  "statistics": {
    "cpu_usage": 0.45,
    "memory_usage": 0.60,
    "gpu_usage": 0.80
  }
}

Response 200:
{
  "success": true,
  "data": {
    "pending_commands": [
      {
        "type": "cancel_job",
        "job_id": "uuid"
      }
    ]
  }
}
```

#### 获取 Worker 列表

```http
GET /api/v1/workers?status=busy&type=gpu
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "worker-gpu-01",
      "status": "busy",
      "type": "gpu",
      "current_job_id": "uuid",
      "last_heartbeat": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 获取 Worker 详情

```http
GET /api/v1/workers/{worker_id}
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "worker-gpu-01",
    "status": "busy",
    "type": "gpu",
    "capabilities": { ... },
    "statistics": {
      "jobs_completed": 150,
      "jobs_failed": 2,
      "total_runtime_seconds": 36000
    }
  }
}
```

#### 注销 Worker

```http
POST /api/v1/workers/{worker_id}/unregister
Authorization: Bearer <worker_token>

Response 204: No Content
```

### 4. Artifact 管理

#### 创建 Artifact

```http
POST /api/v1/artifacts
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "original_video.mp4",
  "type": "video",
  "project_id": "uuid",
  "job_id": "uuid",
  "module_id": "M01",
  "mime_type": "video/mp4"
}

Response 201:
{
  "success": true,
  "data": {
    "id": "uuid",
    "upload_url": "https://minio.../put-object",
    "status": "pending"
  }
}
```

#### 上传 Artifact 数据

```http
PUT https://minio.../put-object
Content-Type: video/mp4
Content-Length: 102400000

<binary data>

Response 200:
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "ready",
    "size_bytes": 102400000,
    "checksum": "sha256..."
  }
}
```

#### 下载 Artifact

```http
GET /api/v1/artifacts/{artifact_id}/download
Authorization: Bearer <token>

Response 302: Redirect to signed URL
Location: https://minio.../get-object?expires=...

或者直接流式传输:
Response 200:
Content-Type: video/mp4
Content-Disposition: attachment; filename="video.mp4"

<binary data>
```

#### 获取 Artifact 信息

```http
GET /api/v1/artifacts/{artifact_id}
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "original_video.mp4",
    "type": "video",
    "status": "ready",
    "size_bytes": 102400000,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

#### 列出项目 Artifacts

```http
GET /api/v1/projects/{project_id}/artifacts?type=video
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": [ ... ],
  "pagination": { ... }
}
```

#### 删除 Artifact

```http
DELETE /api/v1/artifacts/{artifact_id}
Authorization: Bearer <token>

Response 204: No Content
```

### 5. 工作流管理

#### 获取工作流列表

```http
GET /api/v1/workflows?is_active=true
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": [ ... ]
}
```

#### 获取工作流详情

```http
GET /api/v1/workflows/{workflow_id}
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "标准单集工作流",
    "type": "single_episode",
    "definition": {
      "nodes": [ ... ],
      "edges": [ ... ]
    }
  }
}
```

#### 创建工作流

```http
POST /api/v1/workflows
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "自定义工作流",
  "type": "custom",
  "definition": { ... }
}

Response 201:
{
  "success": true,
  "data": { ... }
}
```

### 6. 人物数据库

#### 创建人物

```http
POST /api/v1/projects/{project_id}/characters
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Walter White",
  "name_en": "Walter White",
  "gender": "male",
  "age_range": "adult",
  "role_type": "main",
  "actor_name": "Bryan Cranston",
  "description": "高中化学老师，后成为毒品制造者"
}

Response 201:
{
  "success": true,
  "data": { ... }
}
```

#### 获取人物列表

```http
GET /api/v1/projects/{project_id}/characters
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": [ ... ]
}
```

#### 更新人物

```http
PATCH /api/v1/characters/{character_id}
Content-Type: application/json
Authorization: Bearer <token>

{
  "description": "Updated description"
}

Response 200:
{
  "success": true,
  "data": { ... }
}
```

### 7. 音色档案

#### 创建 Voice Profile

```http
POST /api/v1/projects/{project_id}/voice-profiles
Content-Type: application/json
Authorization: Bearer <token>

{
  "character_id": "uuid",
  "name": "VOICE-WALTER-V01",
  "tts_model": "cosyvoice",
  "tts_config": { ... }
}

Response 201:
{
  "success": true,
  "data": { ... }
}
```

### 8. 统计和监控

#### 获取系统统计

```http
GET /api/v1/statistics/overview
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": {
    "projects": {
      "total": 100,
      "pending": 10,
      "processing": 50,
      "completed": 30,
      "failed": 10
    },
    "jobs": {
      "total": 1000,
      "running": 200,
      "pending": 100,
      "completed": 600,
      "failed": 100
    },
    "workers": {
      "total": 10,
      "online": 8,
      "offline": 2
    },
    "artifacts": {
      "total": 5000,
      "total_size_gb": 1024
    }
  }
}
```

#### 获取 Worker 统计

```http
GET /api/v1/workers/{worker_id}/statistics
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": {
    "jobs_completed": 150,
    "jobs_failed": 2,
    "total_runtime_seconds": 36000,
    "average_job_time_seconds": 240,
    "success_rate": 0.987
  }
}
```

## 认证

### 获取 Token

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user",
  "password": "pass"
}

Response 200:
{
  "success": true,
  "data": {
    "access_token": "jwt_token",
    "refresh_token": "refresh_token",
    "expires_in": 3600
  }
}
```

### 刷新 Token

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "refresh_token"
}

Response 200:
{
  "success": true,
  "data": {
    "access_token": "new_jwt_token",
    "expires_in": 3600
  }
}
```

## WebSocket API

### 实时作业状态

```javascript
// 连接
ws://api.example.com/ws/jobs/{job_id}?token=jwt_token

// 消息格式
{
  "type": "job_progress",
  "data": {
    "job_id": "uuid",
    "progress": 45,
    "status": "running",
    "message": "Processing frame 4500/10000"
  }
}

{
  "type": "job_completed",
  "data": {
    "job_id": "uuid",
    "status": "completed",
    "output_artifacts": [ ... ]
  }
}

{
  "type": "job_failed",
  "data": {
    "job_id": "uuid",
    "status": "failed",
    "error": {
      "code": "PROCESSING_ERROR",
      "message": "Video processing failed"
    }
  }
}
```

### 系统事件

```javascript
// 连接
ws://api.example.com/ws/events?token=jwt_token

// 消息格式
{
  "type": "worker_registered",
  "data": {
    "worker_id": "uuid",
    "name": "worker-gpu-01"
  }
}

{
  "type": "worker_offline",
  "data": {
    "worker_id": "uuid",
    "name": "worker-gpu-01"
  }
}
```

## 错误代码

| 代码 | HTTP 状态 | 描述 |
|------|----------|------|
| `UNAUTHORIZED` | 401 | 未认证或 Token 无效 |
| `FORBIDDEN` | 403 | 权限不足 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `VALIDATION_ERROR` | 400 | 请求参数验证失败 |
| `CONFLICT` | 409 | 资源冲突 |
| `RATE_LIMIT_EXCEEDED` | 429 | 超过限流阈值 |
| `INTERNAL_ERROR` | 500 | 内部服务器错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |
| `ARTIFACT_NOT_FOUND` | 404 | Artifact 不存在 |
| `ARTIFACT_UPLOAD_FAILED` | 500 | Artifact 上传失败 |
| `JOB_NOT_FOUND` | 404 | Job 不存在 |
| `JOB_CANCELLED` | 200 | Job 已取消 |
| `WORKER_OFFLINE` | 503 | Worker 离线 |
| `WORKER_BUSY` | 409 | Worker 忙碌 |

## 限流策略

| 资源 | 限制 |
|------|------|
| 未认证用户 | 100 req/hour |
| 已认证用户 | 1000 req/hour |
| Worker 心跳 | 60 req/minute |
| Artifact 上传 | 10 GB/hour |

## 后续决策

- GraphQL 替代方案
- gRPC 用于 Worker-Orchestrator 通信
- 文件上传的断点续传
