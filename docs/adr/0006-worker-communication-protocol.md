# ADR 0006: Worker 通信协议

## 状态

设计中

## 上下文

Layer 0 和 Worker 之间需要建立可靠的通信协议。Worker 需要接收任务、报告进度、更新状态、下载/上传 Artifact。

## 通信架构

```
┌─────────────────────────────────────────────────────────┐
│                    Layer 0                               │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │            REST API (同步)                        │  │
│  │  • Worker 注册                                    │  │
│  │  • 任务接受/拒绝                                  │  │
│  │  • 状态查询                                      │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │         WebSocket (实时)                         │  │
│  │  • 任务进度推送                                  │  │
│  │  • 系统事件通知                                  │  │
│  │  • 指令推送                                      │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │      Message Queue (异步)                        │  │
│  │  • 心跳报告                                      │  │
│  │  • 状态更新                                      │  │
│  │  • 日志上传                                      │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────┐
│                    Worker                               │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │            HTTP Client                            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │         WebSocket Client                         │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │      Message Queue Client                        │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 协议设计

### 1. Worker 注册协议

#### 请求

```http
POST /api/v1/workers/register
Content-Type: application/json

{
  "worker_id": "uuid",  // 可选，不提供则自动生成
  "name": "worker-gpu-01",
  "type": "gpu",
  "version": "1.0.0",

  // 资源配置
  "resources": {
    "cpu_cores": 8,
    "memory_gb": 32,
    "gpu_count": 1,
    "gpu_memory_gb": 16,
    "storage_gb": 500
  },

  // 能力声明
  "capabilities": {
    "modules": ["M05", "M06", "M09"],
    "features": ["cuda", "tensorrt"],
    "max_concurrent_jobs": 2
  },

  // 网络信息
  "endpoints": {
    "api": "http://192.168.1.100:8001",
    "websocket": "ws://192.168.1.100:8001/ws"
  },

  // 元数据
  "metadata": {
    "hostname": "gpu-server-01",
    "os": "Linux",
    "python_version": "3.11"
  }
}
```

#### 响应

```json
{
  "success": true,
  "data": {
    "worker_id": "uuid",
    "status": "idle",
    "registration_time": "2024-01-01T00:00:00Z",

    // 认证凭证
    "credentials": {
      "worker_token": "jwt_token_for_api_calls",
      "websocket_url": "wss://api.example.com/ws/workers/{worker_id}",
      "heartbeat_interval": 10,
      "heartbeat_max_miss": 3
    },

    // 配置
    "config": {
      "artifact_storage": {
        "type": "minio",
        "endpoint": "minio.example.com:9000",
        "credentials": {
          "access_key": "...",
          "secret_key": "..."
        }
      },
      "log_upload": {
        "enabled": true,
        "endpoint": "https://logs.example.com"
      }
    }
  }
}
```

### 2. 任务分配协议

#### Layer 0 → Worker

```http
POST {worker_api_url}/api/v1/jobs/accept
Content-Type: application/json
Authorization: Bearer {orchestrator_token}

{
  "job_id": "uuid",
  "project_id": "uuid",
  "module_id": "M09",

  // 配置
  "config": {
    "tts_model": "cosyvoice",
    "voice_profile": "VOICE-WALTER-V05",
    "batch_size": 32
  },

  // 输入 Artifact
  "input_artifacts": [
    {
      "id": "uuid",
      "name": "dialogue.json",
      "type": "dialogue_timeline",
      "download_url": "https://minio.../dialogue.json?expires=3600",
      "checksum": "sha256:...",
      "size_bytes": 1024000
    }
  ],

  // 输出规范
  "output_specs": [
    {
      "name": "generated_audio",
      "type": "audio",
      "format": "wav",
      "compression": "none"
    }
  ],

  // 约束
  "constraints": {
    "timeout_seconds": 3600,
    "max_memory_gb": 16,
    "require_gpu": true
  },

  // 优先级
  "priority": 7
}
```

#### Worker 响应（接受）

```json
{
  "success": true,
  "data": {
    "job_id": "uuid",
    "status": "accepted",
    "estimated_start_time": "2024-01-01T00:00:10Z",
    "estimated_completion_time": "2024-01-01T00:30:00Z"
  }
}
```

#### Worker 响应（拒绝）

```json
{
  "success": false,
  "error": {
    "code": "JOB_REJECTED",
    "message": "Insufficient resources",
    "details": {
      "reason": "gpu_memory_required_16gb_but_only_8gb_available"
    }
  }
}
```

### 3. 进度报告协议

#### Worker → Layer 0 (WebSocket)

```javascript
// 连接
wss://api.example.com/ws/workers/{worker_id}?token={worker_token}

// 发送进度更新
{
  "type": "job_progress",
  "data": {
    "job_id": "uuid",
    "progress": 45,  // 0-100
    "status": "running",

    // 详细信息
    "details": {
      "stage": "synthesizing",
      "current_item": 450,
      "total_items": 1000,
      "eta_seconds": 900,
      "current_speed": "50 items/sec"
    },

    // 资源使用
    "resources": {
      "cpu_usage": 0.65,
      "memory_usage": 0.72,
      "gpu_usage": 0.85,
      "gpu_memory_mb": 8192
    },

    // 日志
    "logs": [
      {
        "level": "info",
        "message": "Processing dialogue line 450",
        "timestamp": "2024-01-01T00:15:00Z"
      }
    ]
  }
}

// 完成
{
  "type": "job_completed",
  "data": {
    "job_id": "uuid",
    "status": "completed",
    "progress": 100,

    // 输出 Artifact
    "output_artifacts": [
      {
        "id": "uuid",
        "name": "walter_cn_audio.wav",
        "type": "audio",
        "upload_url": "https://minio.../put-object",
        "size_bytes": 20480000,
        "checksum": "sha256:...",
        "metadata": {
          "duration_seconds": 1200,
          "sample_rate": 44100,
          "channels": 1
        }
      }
    ],

    // 统计
    "statistics": {
      "duration_seconds": 1800,
      "items_processed": 1000,
      "average_speed": "0.56 items/sec"
    }
  }
}

// 失败
{
  "type": "job_failed",
  "data": {
    "job_id": "uuid",
    "status": "failed",
    "error": {
      "code": "TTS_ERROR",
      "message": "Voice synthesis failed",
      "stack_trace": "...",

      // 是否可重试
      "retryable": true,
      "retry_delay_seconds": 60
    },

    // 部分结果
    "partial_output": [
      {
        "artifact_id": "uuid",
        "items_completed": 450
      }
    ]
  }
}
```

#### Layer 0 → Worker (WebSocket - 指令)

```javascript
// 取消任务
{
  "type": "command",
  "data": {
    "command": "cancel_job",
    "job_id": "uuid",
    "reason": "User requested cancellation"
  }
}

// 暂停任务
{
  "type": "command",
  "data": {
    "command": "pause_job",
    "job_id": "uuid"
  }
}

// 恢复任务
{
  "type": "command",
  "data": {
    "command": "resume_job",
    "job_id": "uuid"
  }
}

// 更新配置
{
  "type": "command",
  "data": {
    "command": "update_config",
    "job_id": "uuid",
    "config": {
      "batch_size": 16
    }
  }
}

// 系统关闭
{
  "type": "command",
  "data": {
    "command": "shutdown",
    "reason": "System maintenance",
    "grace_period_seconds": 300
  }
}
```

### 4. 心跳协议

#### Worker → Layer 0 (HTTP POST)

```http
POST /api/v1/workers/{worker_id}/heartbeat
Content-Type: application/json
Authorization: Bearer {worker_token}

{
  "timestamp": "2024-01-01T00:00:00Z",
  "status": "busy",

  // 当前任务
  "current_job": {
    "job_id": "uuid",
    "progress": 45,
    "running_seconds": 900
  },

  // 资源状态
  "resources": {
    "cpu_usage": 0.65,
    "memory_usage": 0.72,
    "gpu_usage": 0.85,
    "disk_usage_gb": 250,
    "network_mbps": 100
  },

  // 队列状态
  "queue": {
    "pending": 2,
    "running": 1
  },

  // 统计
  "statistics": {
    "jobs_completed": 150,
    "jobs_failed": 2,
    "total_uptime_seconds": 86400
  },

  // 健康检查
  "health": {
    "status": "healthy",
    "checks": {
      "disk": "ok",
      "memory": "ok",
      "gpu": "ok"
    }
  }
}
```

#### Layer 0 响应

```json
{
  "success": true,
  "data": {
    // 待处理指令
    "pending_commands": [
      {
        "command": "cancel_job",
        "job_id": "uuid",
        "issued_at": "2024-01-01T00:00:00Z"
      }
    ],

    // 配置更新
    "config_updates": {
      "heartbeat_interval": 15,
      "log_level": "debug"
    },

    // 服务器时间
    "server_time": "2024-01-01T00:00:00Z"
  }
}
```

### 5. Artifact 传输协议

#### 下载

```http
GET /api/v1/artifacts/{artifact_id}/download
Authorization: Bearer {worker_token}

Response:
302 Found
Location: https://minio.example.com/bucket/path?signature=...&expires=...

或者流式传输:
200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="artifact.bin"
Content-Length: 102400000

<binary data>
```

#### 上传

```http
POST /api/v1/artifacts/{artifact_id}/upload
Authorization: Bearer {worker_token}

Response:
200 OK
{
  "success": true,
  "data": {
    "upload_url": "https://minio.example.com/...",
    "upload_method": "PUT",
    "headers": {
      "Content-Type": "application/octet-stream",
      "X-Amz-Date": "..."
    },
    "expires_in": 3600
  }
}

// Worker 使用返回的 URL 上传
PUT {upload_url}
Content-Type: application/octet-stream
Content-Length: 102400000

<binary data>

Response: 200 OK
```

### 6. 日志上传协议

#### Worker → Layer 0 (批量上传)

```http
POST /api/v1/logs/upload
Content-Type: application/json
Authorization: Bearer {worker_token}

{
  "worker_id": "uuid",
  "job_id": "uuid",
  "logs": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "level": "info",
      "logger": "worker.tts",
      "message": "Starting synthesis",
      "extra": {
        "model": "cosyvoice",
        "voice": "walter"
      }
    }
  ]
}

Response:
200 OK
{
  "success": true,
  "data": {
    "accepted": 1
  }
}
```

## 消息格式规范

### 统一消息信封

```json
{
  "version": "1.0",
  "message_id": "uuid",
  "timestamp": "2024-01-01T00:00:00Z",
  "type": "job_progress",
  "source": "worker",
  "destination": "orchestrator",
  "correlation_id": "uuid",  // 用于关联请求响应
  "payload": { ... }
}
```

### 错误消息格式

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": { ... },
    "retryable": true,
    "retry_after_seconds": 60
  }
}
```

## 安全性

### 1. 认证

- **Worker Token**: JWT Token，包含 Worker ID 和权限
- **Orchestrator Token**: 用于 Layer 0 调用 Worker API
- **Token 刷新**: Worker Token 定期刷新

### 2. 加密

- **传输加密**: TLS 1.3
- **Artifact 加密**: 可选的 Artifact 端到端加密
- **敏感数据**: 配置文件中的密钥加密存储

### 3. 授权

- **Worker 只能访问**: 分配给它的任务、相关 Artifact
- **最小权限原则**: Worker Token 只包含必要权限

## 可靠性保证

### 1. 消息确认

```javascript
// 发送重要消息时要求确认
{
  "type": "job_progress",
  "require_ack": true,
  "ack_timeout": 30
}

// 接收方确认
{
  "type": "ack",
  "message_id": "uuid",
  "status": "received"
}
```

### 2. 消息重试

- WebSocket 断线重连
- 指数退避重试
- 最大重试次数限制

### 3. 心跳机制

- Worker 定期心跳（默认 10 秒）
- Layer 0 检测心跳超时（60 秒）
- 超时后标记 Worker 离线

### 4. 状态一致性

- 状态更新幂等性
- 状态冲突解决（以最新状态为准）
- 定期状态同步

## 性能优化

### 1. 批量操作

```javascript
// 批量进度更新
{
  "type": "batch_progress",
  "data": {
    "updates": [
      {"job_id": "uuid1", "progress": 45},
      {"job_id": "uuid2", "progress": 30}
    ]
  }
}
```

### 2. 压缩

- 日志批量压缩上传
- 大 Artifact 分块传输

### 3. 连接复用

- HTTP/2 多路复用
- WebSocket 长连接

## 监控和诊断

### 1. 连接状态监控

- WebSocket 连接状态
- 消息延迟
- 消息丢失率

### 2. 性能指标

- 消息吞吐量
- API 响应时间
- Artifact 传输速度

### 3. 诊断端点

```http
GET /api/v1/workers/{worker_id}/diagnostics

Response:
{
  "connections": {
    "websocket": {
      "status": "connected",
      "connected_at": "2024-01-01T00:00:00Z",
      "messages_sent": 1000,
      "messages_received": 800
    },
    "api": {
      "last_heartbeat": "2024-01-01T00:00:00Z",
      "successful_requests": 500,
      "failed_requests": 2
    }
  },
  "queues": {
    "pending_messages": 10,
    "pending_logs": 5
  }
}
```

## 后续决策

- 是否使用 gRPC 替代 HTTP/WebSocket
- 消息队列选择（Redis Stream、RabbitMQ、Kafka）
- 是否支持 Worker 间直接通信（某些场景）
