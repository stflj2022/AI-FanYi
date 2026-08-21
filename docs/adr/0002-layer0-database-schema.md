# ADR 0002: Layer 0 数据库 Schema 设计

## 状态

设计中

## 上下文

Layer 0 需要管理项目、作业、工作流、Artifact、Worker 等核心实体。需要设计一个合理的数据库 Schema。

## 核心实体

### 1. Project (项目)

**一个完整的配音工程**，对应一部电视剧、一季或单集。

```sql
CREATE TYPE project_status AS ENUM (
    'pending',      -- 待处理
    'intake',       -- 输入中
    'processing',   -- 处理中
    'review',       -- 审查中
    'completed',    -- 已完成
    'failed',       -- 失败
    'archived'      -- 已归档
);

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status project_status DEFAULT 'pending',

    -- 元数据
    media_type VARCHAR(50),           -- movie, tv_series, documentary
    title VARCHAR(255),               -- 剧名
    title_en VARCHAR(255),            -- 英文名
    season INTEGER,                   -- 季数
    episode INTEGER,                  -- 集数
    year INTEGER,                     -- 年份
    original_language VARCHAR(10),    -- 原语言
    target_language VARCHAR(10) DEFAULT 'zh-CN',

    -- 外部数据源
    tmdb_id INTEGER,
    imdb_id VARCHAR(20),

    -- 时间
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- 用户
    created_by UUID,
    assigned_to UUID,

    -- 配置
    workflow_id UUID REFERENCES workflows(id),
    config JSONB,                     -- 项目配置

    INDEX idx_project_status (status),
    INDEX idx_project_tmdb (tmdb_id),
    INDEX idx_project_created (created_at)
);
```

### 2. Job (作业)

**Project 中的一个处理单元**，通常对应一集。

```sql
CREATE TYPE job_status AS ENUM (
    'pending',      -- 待处理
    'scheduled',   -- 已调度
    'running',      -- 运行中
    'waiting',      -- 等待依赖
    'completed',    -- 已完成
    'failed',       -- 失败
    'cancelled',    -- 已取消
    'retrying'      -- 重试中
);

CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status job_status DEFAULT 'pending',

    -- 执行信息
    module_id VARCHAR(20),             -- 执行的模块 ID (M01-M14)
    worker_id UUID,                    -- 执行的 Worker
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- 依赖
    depends_on UUID[],                 -- 依赖的 Job ID 列表

    -- 时间
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    scheduled_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- 输入输出
    input_artifacts UUID[],            -- 输入 Artifact ID
    output_artifacts UUID[],           -- 输出 Artifact ID

    -- 错误信息
    error_message TEXT,
    error_stack TEXT,

    INDEX idx_job_project (project_id),
    INDEX idx_job_status (status),
    INDEX idx_job_module (module_id),
    INDEX idx_job_worker (worker_id)
);
```

### 3. Workflow (工作流)

**定义 Module 的执行顺序和依赖关系**。

```sql
CREATE TYPE workflow_type AS ENUM (
    'single_episode',    -- 单集处理
    'batch_season',     -- 批量季处理
    'batch_series',     -- 批量全集处理
    'custom'            -- 自定义
);

CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type workflow_type DEFAULT 'single_episode',

    -- 工作流定义 (DAG)
    definition JSONB NOT NULL,         -- DAG 结构
    -- 示例:
    -- {
    --   "nodes": [
    --     {"id": "m01", "module": "M01", "config": {...}},
    --     {"id": "m02", "module": "M02", "config": {...}}
    --   ],
    --   "edges": [
    --     {"from": "m01", "to": "m02"},
    --     {"from": "m02", "to": "m03"}
    --   ]
    -- }

    -- 版本控制
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_workflow_type (type),
    INDEX idx_workflow_active (is_active)
);
```

### 4. Artifact (工件)

**模块之间的数据传递接口**。

```sql
CREATE TYPE artifact_type AS ENUM (
    -- 媒体类型
    'video', 'audio', 'subtitle',
    -- 数据类型
    'metadata', 'character_db', 'voice_db',
    'dialogue_timeline', 'scene_timeline',
    'analysis_result', 'synthesis_config',
    -- 输出类型
    'final_video', 'qa_report',
    -- 其他
    'archive', 'log', 'other'
);

CREATE TYPE artifact_status AS ENUM (
    'pending',      -- 待创建
    'uploading',    -- 上传中
    'processing',   -- 处理中
    'ready',        -- 就绪
    'failed',       -- 失败
    'archived'      -- 已归档
);

CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type artifact_type NOT NULL,
    status artifact_status DEFAULT 'pending',

    -- 归属
    project_id UUID REFERENCES projects(id),
    job_id UUID REFERENCES jobs(id),
    module_id VARCHAR(20),             -- 生成此 Artifact 的模块

    -- 存储
    storage_type VARCHAR(20) DEFAULT 'minio',  -- minio, local, s3
    storage_path TEXT,                 -- 存储路径
    storage_bucket VARCHAR(100),        -- 存储桶

    -- 元数据
    size_bytes BIGINT,
    mime_type VARCHAR(100),
    checksum VARCHAR(64),               -- SHA256
    metadata JSONB,                     -- 额外元数据

    -- 版本
    version INTEGER DEFAULT 1,
    parent_artifact_id UUID,            -- 基于哪个 Artifact 版本

    -- 引用计数 (用于清理)
    ref_count INTEGER DEFAULT 0,

    -- 时间
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    accessed_at TIMESTAMP,

    INDEX idx_artifact_project (project_id),
    INDEX idx_artifact_job (job_id),
    INDEX idx_artifact_type (type),
    INDEX idx_artifact_status (status)
);
```

### 5. Worker (工作节点)

**执行模块的 Worker 节点**。

```sql
CREATE TYPE worker_status AS ENUM (
    'offline',      -- 离线
    'idle',         -- 空闲
    'busy',         -- 忙碌
    'starting',     -- 启动中
    'stopping',     -- 停止中
    'error'         -- 错误
);

CREATE TYPE worker_type AS ENUM (
    'cpu',          -- CPU Worker
    'gpu',          -- GPU Worker
    'io',           -- I/O Worker
    'hybrid'        -- 混合 Worker
);

CREATE TABLE workers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    status worker_status DEFAULT 'offline',
    type worker_type DEFAULT 'cpu',

    -- 能力
    capabilities JSONB,                 -- 支持的模块列表
    -- 示例: {"modules": ["M01", "M02", "M09"], "gpu": true}

    -- 资源
    cpu_cores INTEGER,
    memory_gb INTEGER,
    gpu_count INTEGER DEFAULT 0,
    gpu_memory_gb INTEGER DEFAULT 0,

    -- 当前任务
    current_job_id UUID REFERENCES jobs(id),

    -- 统计
    jobs_completed INTEGER DEFAULT 0,
    jobs_failed INTEGER DEFAULT 0,
    total_runtime_seconds BIGINT DEFAULT 0,

    -- 心跳
    last_heartbeat TIMESTAMP,
    heartbeat_interval_seconds INTEGER DEFAULT 10,

    -- 位置
    host VARCHAR(100),
    port INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_worker_status (status),
    INDEX idx_worker_type (type),
    INDEX idx_worker_heartbeat (last_heartbeat)
);
```

### 6. Character DB (人物数据库)

**长期资产**。

```sql
CREATE TABLE characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),

    -- 基本信息
    name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    aliases TEXT[],                     -- 别名列表

    -- 属性
    gender VARCHAR(20),
    age_range VARCHAR(20),              -- child, teen, young_adult, adult, senior
    role_type VARCHAR(50),              -- main, supporting, minor, cameo

    -- 演员信息
    actor_name VARCHAR(255),
    actor_id UUID,

    -- 描述
    description TEXT,
    personality TEXT,                   -- 性格特点
    speech_pattern TEXT,               -- 说话特点

    -- 关系
    relationships JSONB,                -- 人物关系

    -- 首次出现
    first_appearance_season INTEGER,
    first_appearance_episode INTEGER,
    first_appearance_timestamp DECIMAL,

    -- 状态
    is_active BOOLEAN DEFAULT true,
    voice_profile_id UUID,              -- 关联的 Voice Profile

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(project_id, name),
    INDEX idx_character_project (project_id),
    INDEX idx_character_actor (actor_id)
);
```

### 7. Voice Profile (音色档案)

```sql
CREATE TABLE voice_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID NOT NULL REFERENCES characters(id),
    project_id UUID NOT NULL REFERENCES projects(id),

    -- 基本信息
    name VARCHAR(255) NOT NULL,        -- VOICE-WALTER-V05
    version VARCHAR(20),                -- v1.0, v2.0

    -- TTS 配置
    tts_model VARCHAR(100),             -- cosyvoice, f5-tts
    tts_model_version VARCHAR(50),
    tts_config JSONB,                   -- 模型特定配置

    -- 声音特征 (参考值)
    pitch_range VARCHAR(20),            -- low, medium, high
    speed_range VARCHAR(20),            -- slow, medium, fast
    emotional_range TEXT[],            -- 支持的情绪类型

    -- 参考音频
    reference_audio_artifact_id UUID REFERENCES artifacts(id),

    -- 状态
    is_active BOOLEAN DEFAULT true,
    is_validated BOOLEAN DEFAULT false,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(project_id, character_id, version),
    INDEX idx_voice_profile_character (character_id),
    INDEX idx_voice_profile_project (project_id)
);
```

## 索引策略

1. **外键索引**: 所有外键字段建立索引
2. **状态索引**: 频繁查询的状态字段建立索引
3. **时间索引**: created_at, updated_at 用于范围查询
4. **复合索引**: (project_id, status), (worker_id, status) 等

## 分区策略

对于大型项目，考虑对以下表进行分区：

1. **artifacts**: 按 created_at 时间分区（每月）
2. **jobs**: 按 created_at 时间分区（每月）
3. **logs**: 如果有日志表，按时间分区

## 数据清理策略

1. **Artifact 清理**:
   - ref_count = 0 且超过 30 天未访问
   - 使用软删除，标记为 archived

2. **Job 清理**:
   - 已完成超过 90 天的 Job 详情
   - 保留统计信息

3. **Worker 心跳**:
   - 超过 60 秒无心跳标记为 offline

## 迁移策略

使用 Alembic 进行数据库迁移：

```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

## 后续决策

- 是否需要全文搜索 (PostgreSQL FTS 或 Elasticsearch)
- 时区处理策略
- 数据库备份策略
