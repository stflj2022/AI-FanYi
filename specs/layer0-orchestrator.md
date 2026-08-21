# Layer 0 Orchestrator - 总调度中心

## 概述

Layer 0 编排器是影视AI配音平台的总调度中心，负责整个系统的协调、管理和监控。它不直接进行 ASR、翻译、TTS 或视频处理，而是调度和管理各生产模块。

## 核心职责

1. **项目和作业管理**: 创建项目、作业，管理工作流和状态
2. **Artifact 管理**: 管理 Artifact Registry，处理模块间数据传递
3. **资源调度**: 管理 GPU/CPU 资源，分配 Worker
4. **工作流编排**: 定义和执行 DAG 工作流
5. **失败检测和自动重试**: 监控任务状态，自动重试失败任务
6. **断点恢复**: 系统崩溃后从任意 Artifact 恢复
7. **日志和状态监控**: 提供实时监控和日志查询
8. **Web UI**: 提供用户界面
9. **项目级数据库调用**: 管理所有数据库操作
10. **最终归档**: 项目完成后的归档处理

## 技术栈

- **语言**: Python 3.11+
- **Web 框架**: FastAPI
- **数据库**: PostgreSQL (使用 SQLAlchemy ORM)
- **缓存**: Redis
- **消息队列**: Redis Stream / Kafka (可选)
- **存储**: MinIO (S3-compatible)
- **监控**: Prometheus + Grafana
- **日志**: Loki / ELK
- **追踪**: Jaeger / OpenTelemetry

## 数据库 Schema

参见 `docs/adr/0002-layer0-database-schema.md`

### 核心表

1. `projects` - 项目表
2. `jobs` - 作业表
3. `workflows` - 工作流表
4. `artifacts` - 工件表
5. `workers` - 工作节点表
6. `characters` - 人物表
7. `voice_profiles` - 音色档案表
8. `error_log` - 错误日志表

## API 端点

参见 `docs/adr/0004-rest-api-specification.md`

### 主要端点

- `POST /api/v1/projects` - 创建项目
- `GET /api/v1/projects/{project_id}` - 获取项目详情
- `GET /api/v1/projects/{project_id}/jobs` - 获取作业列表
- `POST /api/v1/projects/{project_id}/jobs` - 创建作业
- `POST /api/v1/workers/register` - Worker 注册
- `POST /api/v1/workers/{worker_id}/heartbeat` - Worker 心跳
- `GET /api/v1/artifacts/{artifact_id}` - 获取 Artifact 信息
- `GET /api/v1/statistics/overview` - 获取系统统计

## 核心组件

### 1. 调度器 (Scheduler)

参见 `docs/adr/0005-scheduler-algorithm.md`

**职责**:
- 依赖解析 (DAG)
- 资源匹配
- 任务分发
- 失败重试

### 2. Artifact Registry

参见 `docs/adr/0003-artifact-registry-interface.md`

**职责**:
- Artifact 创建和上传
- Artifact 下载和检索
- 版本管理
- 引用计数和清理

### 3. Worker 管理器

参见 `docs/adr/0006-worker-communication-protocol.md`

**职责**:
- Worker 注册和认证
- 心跳监控
- 状态更新
- 指令下发

### 4. 错误处理器

参见 `docs/adr/0007-error-handling-retry-strategy.md`

**职责**:
- 错误分类和记录
- 自动重试调度
- 熔断器
- 降级策略

### 5. 监控和日志系统

参见 `docs/adr/0008-monitoring-logging-system.md`

**职责**:
- 指标采集和暴露
- 日志采集和存储
- 分布式追踪
- 告警规则

## 目录结构

```
src/filmdub/
├── core/
│   ├── __init__.py
│   ├── config.py              # 配置管理
│   ├── database.py            # 数据库连接和会话
│   ├── models.py              # SQLAlchemy 模型
│   ├── repositories.py        # 数据访问层
│   ├── storage.py             # 存储抽象层
│   └── cache.py               # 缓存抽象层
│
├── orchestrator/
│   ├── __init__.py
│   ├── scheduler.py           # 调度器
│   ├── artifact_registry.py   # Artifact Registry
│   ├── worker_manager.py      # Worker 管理器
│   ├── error_handler.py       # 错误处理器
│   ├── workflow_engine.py     # 工作流引擎
│   └── metrics_collector.py   # 指标采集器
│
├── apps/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI 应用
│   │   ├── dependencies.py    # 依赖注入
│   │   ├── middleware.py      # 中间件
│   │   ├── routers/
│   │   │   ├── projects.py    # 项目 API
│   │   │   ├── jobs.py        # 作业 API
│   │   │   ├── workers.py     # Worker API
│   │   │   ├── artifacts.py   # Artifact API
│   │   │   ├── workflows.py   # 工作流 API
│   │   │   ├── characters.py  # 人物 API
│   │   │   └── statistics.py  # 统计 API
│   │   └── websocket/
│   │       └── handler.py     # WebSocket 处理
│   │
│   └── web/
│       ├── package.json
│       ├── src/
│       │   ├── components/
│       │   ├── pages/
│       │   ├── services/
│       │   └── App.tsx
│       └── public/
│
└── tests/
    ├── test_scheduler.py
    ├── test_artifact_registry.py
    ├── test_worker_manager.py
    └── test_api/
```

## 配置示例

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 应用
    app_name: str = "AI-FanYi Orchestrator"
    app_version: str = "1.0.0"
    debug: bool = False

    # 数据库
    database_url: str = "postgresql://user:pass@localhost/filmdub"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "filmdub-artifacts"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Worker
    worker_heartbeat_interval: int = 10
    worker_heartbeat_timeout: int = 60

    # 监控
    metrics_port: int = 9090
    jaeger_endpoint: str = "localhost:6831"

    class Config:
        env_file = ".env"
```

## 依赖模块

Layer 0 依赖以下模块：
- **M01-M03**: 已实现 (src/filmdub/workers/)

## 与 Worker 通信协议

参见 `docs/adr/0006-worker-communication-protocol.md`

### 通信方式

1. **REST API**: 同步通信 (注册、任务接受、状态查询)
2. **WebSocket**: 实时通信 (进度推送、指令下发)
3. **Message Queue**: 异步通信 (心跳、日志上传)

## 实现优先级

### Phase 1: 核心基础设施 (高优先级)
1. 数据库模型和迁移
2. Artifact Registry (MinIO 集成)
3. 基础 REST API (项目、作业)
4. Worker 注册和心跳

### Phase 2: 调度系统 (高优先级)
1. 调度器核心 (依赖解析、资源匹配)
2. 工作流引擎 (DAG 执行)
3. Worker 管理器 (状态跟踪)
4. 错误处理和重试

### Phase 3: 完善功能 (中优先级)
1. WebSocket 实时通信
2. 监控和日志系统
3. 人物数据库 API
4. 音色档案 API

### Phase 4: Web 前端 (中优先级)
1. React 项目搭建
2. 项目管理界面
3. 作业监控界面
4. Worker 监控界面

### Phase 5: 高级功能 (低优先级)
1. 批量/季集流水线 (M13)
2. 项目归档 (M14)
3. 质量控制 (M12) 集成
4. 高级分析和报表

## 测试策略

参见 `docs/adr/0013-testing-strategy.md`

### 测试类型

1. **单元测试**: 每个组件独立测试
2. **集成测试**: 组件间交互测试
3. **端到端测试**: 完整工作流测试
4. **性能测试**: 负载和压力测试
5. **故障注入测试**: 容错能力测试

## 部署要求

- **CPU**: 4+ cores
- **内存**: 8GB+
- **存储**: 100GB+ (用于数据库和日志)
- **网络**: 千兆网络
- **数据库**: PostgreSQL 14+
- **缓存**: Redis 6+
- **对象存储**: MinIO 或 S3-compatible

## 安全考虑

1. **认证**: JWT Token 认证
2. **授权**: 基于角色的访问控制 (RBAC)
3. **加密**: TLS 传输加密，敏感数据加密存储
4. **审计**: 所有关键操作审计日志
5. **限流**: API 限流防止滥用

## 监控指标

- 系统资源 (CPU、内存、磁盘、网络)
- API 性能 (请求速率、延迟、错误率)
- Job 状态 (队列深度、吞吐量、失败率)
- Worker 状态 (在线数、负载、健康度)
- Artifact 存储 (使用量、上传/下载速度)

## 参考 ADR

- ADR 0001: 基于 Artifact 的模块架构
- ADR 0002: Layer 0 数据库 Schema 设计
- ADR 0003: Artifact Registry 接口设计
- ADR 0004: REST API 规范
- ADR 0005: 调度器算法设计
- ADR 0006: Worker 通信协议
- ADR 0007: 错误处理和重试策略
- ADR 0008: 监控和日志系统
