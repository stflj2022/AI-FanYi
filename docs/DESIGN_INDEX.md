# 影视AI配音平台 - 设计文档总览

## 文档结构

### 架构决策记录 (ADR)

本项目使用 ADR (Architecture Decision Records) 记录重要架构和技术决策，共 24 个文档：

```
docs/adr/
├── 系统架构设计 (0001-0008)
│   ├── 0001-artifact-based-architecture.md        # 基于 Artifact 的模块架构
│   ├── 0002-layer0-database-schema.md             # Layer 0 数据库 Schema
│   ├── 0003-artifact-registry-interface.md        # Artifact Registry 接口
│   ├── 0004-rest-api-specification.md             # REST API 规范
│   ├── 0005-scheduler-algorithm.md                # 调度器算法
│   ├── 0006-worker-communication-protocol.md      # Worker 通信协议
│   ├── 0007-error-handling-retry-strategy.md      # 错误处理和重试
│   └── 0008-monitoring-logging-system.md          # 监控和日志系统
│
├── 模块设计 (0009-0011, 0014-0024)
│   ├── 0009-m01-project-media-intake.md           # M01 项目与媒体输入
│   ├── 0010-m04-character-database.md             # M04 人物数据库
│   ├── 0011-m09-voice-synthesis.md                # M09 语音合成
│   ├── 0014-m02-media-analysis.md                 # M02 媒体分析
│   ├── 0015-m03-subtitle-acquisition.md           # M03 字幕与对白获取
│   ├── 0016-m05-audio-scene-analysis.md           # M05 音频与场景分析
│   ├── 0017-m06-speaker-mapping.md                # M06 说话人映射
│   ├── 0018-m07-dialogue-intelligence.md          # M07 对白智能处理
│   ├── 0019-m08-prosody-planning.md               # M08 韵律规划
│   ├── 0020-m10-audio-processing.md               # M10 音频处理
│   ├── 0021-m11-video-assembly.md                 # M11 视频组装
│   ├── 0022-m12-quality-control.md               # M12 质检
│   ├── 0023-m13-batch-pipeline.md                # M13 批量流水线
│   └── 0024-m14-archive.md                       # M14 归档
│
└── 工程实践 (0012-0013)
    ├── 0012-database-migration-design.md          # 数据库迁移
    └── 0013-testing-strategy.md                   # 测试策略
```

## 模块依赖关系图

```
                    ┌─────────────────────────────────────┐
                    │              Layer 0               │
                    │   (调度器 / API / Worker 管理)       │
                    └─────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ↓                  ↓                  ↓
        ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
        │   M01 媒体输入    │  │   M02 媒体分析    │  │  M03 字幕获取     │
        └──────────────────┘  └──────────────────┘  └──────────────────┘
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       ↓
        ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
        │  M04 人物数据库   │  │ M05 音频场景分析  │  │                  │
        └──────────────────┘  └──────────────────┘  │                  │
                    │                  │              │                  │
                    └──────────────────┼──────────────┼──────────────────┘
                                       ↓              ↓
        ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
        │  M06 说话人映射   │  │  M07 对白智能     │  │  M08 韵律规划    │
        └──────────────────┘  └──────────────────┘  └──────────────────┘
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       ↓
        ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
        │  M09 语音合成     │  │ M10 音频处理     │  │ M11 视频组装     │
        └──────────────────┘  └──────────────────┘  └──────────────────┘
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       ↓
        ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
        │  M12 质检         │  │ M13 批量流水线    │  │  M14 归档         │
        └──────────────────┘  └──────────────────┘  └──────────────────┘
```

## 模块概览

| 模块 | 名称 | 输入 Artifact | 输出 Artifact | 核心功能 |
|------|------|---------------|---------------|----------|
| M01 | 项目与媒体输入 | 上传文件 | M01_SourceVideo, M01_MediaMetadata | 媒体上传、验证、解析 |
| M02 | 媒体分析 | M01_SourceVideo | M02_Scenes, M02_Shots | 场景检测、镜头分析 |
| M03 | 字幕与对白获取 | M01_SourceVideo | M03_AlignedSubtitles, M03_DialogueList | 字幕提取、时间对齐 |
| M04 | 人物数据库 | M03_DialogueList, M05_SpeakerEmbeddings | M04_CharacterProfiles | 说话人聚类、人物识别 |
| M05 | 音频与场景分析 | M01_SourceVideo | M05_SpeakerEmbeddings, M05_AudioScenes | 音频分析、说话人识别 |
| M06 | 说话人映射 | M04_CharacterProfiles, M09_VoiceLibrary | M06_SpeakerMappings | 说话人-音色匹配 |
| M07 | 对白智能处理 | M03_AlignedSubtitles | M07_ProcessedDialogues | 翻译、情感标记 |
| M08 | 韵律规划 | M07_ProcessedDialogues | M08_ProsodyPlans | 音高、时长规划 |
| M09 | 语音合成 | M08_ProsodyPlans | M09_SynthesizedAudio | TTS 音频生成 |
| M10 | 音频处理 | M09_SynthesizedAudio | M10_AssembledAudio | 音频拼接、处理 |
| M11 | 视频组装 | M10_AssembledAudio, M01_SourceVideo | M11_FinalVideo | 音视频合成 |
| M12 | 质检 | M11_FinalVideo | M12_QualityReport | 质量检查 |
| M13 | 批量流水线 | 多个项目 | 批量输出 | 批量处理管理 |
| M14 | 归档 | 项目数据 | 归档文件 | 数据归档、清理 |

## 文档阅读顺序

### 对于新加入的开发者

1. **README.md** - 项目概览
2. **CONTEXT.md** - 领域模型和术语
3. **ADR 0001** - 理解整体架构
4. **ADR 0002** - 了解数据模型
5. **ADR 0013** - 了解测试策略

### 对于架构师

1. **ADR 0001** - 架构决策
2. **ADR 0005-0008** - 核心系统设计
3. **ADR 0012** - 数据库迁移
4. **ADR 0013** - 测试策略

### 对于模块开发者

1. **CONTEXT.md** - 理解术语
2. **ADR 0003** - Artifact 接口
3. **ADR 0009-0024** - 模块设计文档
4. **ADR 0013** - 测试要求

## 核心概念速查

| 概念 | 位置 | 说明 |
|------|------|------|
| Layer 0 | CONTEXT.md | 总调度中心 |
| Artifact | ADR 0001 | 模块间数据传递 |
| Module | CONTEXT.md | M01-M14 生产模块 |
| Character DB | ADR 0010 | 人物数据库 |
| Voice Profile | ADR 0010 | 音色档案 |
| Job | ADR 0002 | 处理单元 |
| Workflow | ADR 0002 | 工作流定义 |
| Worker | ADR 0002 | 工作节点 |

## 技术栈概览

### Layer 0
- **语言**: Python 3.11+
- **框架**: FastAPI
- **数据库**: PostgreSQL 15
- **缓存**: Redis 7
- **存储**: MinIO
- **容器**: Docker + Docker Compose

### 媒体处理
- **音视频**: FFmpeg, PyAV, OpenCV
- **ASR**: Whisper, WhisperX
- **说话人识别**: Pyannote.audio

### AI/ML
- **翻译**: Qwen (本地 LLM)
- **TTS**: CosyVoice, F5-TTS (可替换)

## 数据模型关系

```
projects (项目)
    ├─ jobs (作业)
    │   └─ artifacts (工件)
    ├─ characters (人物)
    │   └─ voice_profiles (音色档案)
    └─ workflows (工作流)
        └─ jobs (作业)

workers (工作节点)
    └─ jobs (作业)

artifacts (工件)
    ├─ jobs (作业)
    └─ voice_profiles (音色档案)

batch_projects (批量项目)
    └─ batch_project_members (成员)
        ├─ projects (项目)
        └─ jobs (作业)

archives (归档)
    ├─ projects (项目)
    ├─ jobs (作业)
    └─ batch_projects (批量项目)
```

## 快速开始

### 开发环境设置

```bash
# 1. 克隆项目
git clone <repo_url>
cd AI-FanYi

# 2. 运行初始化脚本
bash scripts/init.sh

# 3. 启动服务
docker-compose up -d

# 4. 运行测试
pytest tests/
```

### 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 开发规范

### 代码结构

```
src/
├── api/                # REST API
│   ├── v1/
│   │   ├── projects.py
│   │   ├── jobs.py
│   │   └── workers.py
│   └── main.py
├── db/                 # 数据库
│   ├── models.py
│   ├── database.py
│   └── migrations/
├── scheduler/          # 调度器
│   ├── resolver.py
│   ├── matcher.py
│   └── dispatcher.py
├── artifacts/          # Artifact Registry
│   ├── registry.py
│   └── storage.py
├── workers/            # Worker 管理
│   └── client.py
├── modules/            # 业务模块
│   ├── m01/  # 项目与媒体输入
│   ├── m02/  # 媒体分析
│   ├── m03/  # 字幕与对白获取
│   ├── m04/  # 人物数据库
│   ├── m05/  # 音频与场景分析
│   ├── m06/  # 说话人映射
│   ├── m07/  # 对白智能处理
│   ├── m08/  # 韵律规划
│   ├── m09/  # 语音合成
│   ├── m10/  # 音频处理
│   ├── m11/  # 视频组装
│   ├── m12/  # 质检
│   ├── m13/  # 批量流水线
│   └── m14/  # 归档
└── utils/              # 工具函数
```

### Git 工作流

```bash
# 功能分支
git checkout -b feature/m01-implementation

# 提交
git commit -m "feat(m01): implement video upload"

# 推送
git push origin feature/m01-implementation

# PR 标题格式
[模块] 简短描述

# 示例
[M01] 实现视频上传功能
[M04] 实现人物数据库
```

## 监控和调试

### 日志级别

- **DEBUG**: 详细调试信息
- **INFO**: 一般信息
- **WARNING**: 警告
- **ERROR**: 错误
- **CRITICAL**: 严重错误

### 关键指标

- **API 请求速率**: requests/sec
- **Job 队列大小**: pending jobs
- **Worker 利用率**: CPU/GPU 使用率
- **Artifact 存储使用**: GB
- **错误率**: % failed requests

### 调试命令

```bash
# 查看日志
docker-compose logs -f api

# 进入容器
docker-compose exec api bash

# 查看数据库
docker-compose exec postgres psql -U filmdubbing -d filmdubbing

# 查看 Redis
docker-compose exec redis redis-cli

# 查看系统状态
curl http://localhost:8000/api/v1/statistics/overview
```

## 测试

### 运行测试

```bash
# 所有测试
pytest

# 单元测试
pytest tests/unit

# 集成测试
pytest tests/integration

# E2E 测试
pytest tests/e2e

# 覆盖率报告
pytest --cov=src --cov-report=html
```

### 测试标记

```bash
# 只运行单元测试
pytest -m unit

# 跳过慢测试
pytest -m "not slow"

# 只运行 GPU 测试
pytest -m gpu
```

## 相关资源

### 文档
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Alembic 文档](https://alembic.sqlalchemy.org/)
- [Docker Compose 文档](https://docs.docker.com/compose/)

### 外部服务
- [TMDB API](https://developers.themoviedb.org/)
- [Whisper](https://github.com/openai/whisper)
- [CosyVoice](https://github.com/FunAudioLLM/CosyVoice)
- [Pyannote.audio](https://github.com/pyannote/pyannote-audio)

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 0.1.0 | 2024-01-21 | 初始设计完成 (13 ADRs) |
| 0.2.0 | 2024-01-21 | 完成所有模块设计 (24 ADRs) |

---

**最后更新**: 2024-01-21

## 下一步选择

### 选项 A: 开始编码

创建 src/ 目录下的代码：
- `src/db/models.py`      - SQLAlchemy 模型
- `src/api/main.py`       - FastAPI 应用
- `src/scheduler/`        - 调度器实现

### 选项 B: 创建 GitHub Issues

使用 Wayfinder 结构创建 GitHub Issues
- Layer 0 相关 tickets
- 各模块 tickets

### 选项 C: Docker 配置优化

- Dockerfile 优化
- docker-compose.yml 完善
- CI/CD 配置

你想继续哪个方向？
