# 影视 AI 配音平台

> 模块化、可替换、可恢复的影视剧中文 AI 配音生产系统

[![CI/CD](https://github.com/your-org/AI-FanYi/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/AI-FanYi/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-latest-blue.svg)](https://www.docker.com/)

## 项目概述

本平台是一套完整的影视后期生产流水线，使没有中文配音的影视剧能够经过自动化处理，最终得到人物身份稳定、音色基本一致、中文表达自然、语速与画面基本同步、情绪基本符合剧情、整体音量统一的中文配音视频。

### 核心目标

- **人物身份稳定**: 同一人物跨集、跨季音色一致
- **音色基本一致**: AI 配音尽量接近原演员声音特征
- **中文表达自然**: 翻译和配音符合中文表达习惯
- **语速与画面同步**: 对白时间轴与视频匹配
- **情绪符合剧情**: 配音情绪与剧情场景一致
- **整体音量统一**: 符合广播标准

## 系统架构

```
                        用户
                         │
                         ▼
                   Web 控制界面
                         │
                         ▼
    ┌──────────────────────────────────────────┐
    │              Layer 0                     │
    │           Orchestrator                   │
    │  工作流/状态/调度/资源/Artifact/恢复       │
    └──────────────────┬───────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
      M01            M02            M03
        ↓              ↓              ↓
       ...            ...            ...
        ↓
      M14
        │
        ▼
              最终配音视频
```

## 模块列表

| 模块 | 名称 | 核心功能 |
|------|------|----------|
| Layer 0 | Orchestrator | 总调度中心，不直接处理媒体 |
| M01 | Project & Media Intake | 项目建立、媒体输入、元数据获取 |
| M02 | Media Analysis | 媒体分析、场景检测、镜头分析 |
| M03 | Subtitle & Dialogue Acquisition | 字幕获取、对白切分 |
| M04 | Character Database Construction | 人物数据库构建 |
| M05 | Audio & Scene Analysis | 音频分析、说话人识别 |
| M06 | Speaker → Character → Voice Identity | 说话人映射到人物 |
| M07 | Subtitle / Dialogue Intelligence | 字幕智能处理、翻译 |
| M08 | Prosody & Performance Planning | 韵律与表演规划 |
| M09 | Voice Synthesis | AI 语音合成 |
| M10 | Dialogue Audio Processing & Scene Mixing | 音频处理与混音 |
| M11 | Video Assembly & Final Encoding | 视频组装与编码 |
| M12 | Project QA & Human Review | 质检与人工审查 |
| M13 | Batch / Season Pipeline | 批量/季集处理 |
| M14 | Project Archive & Reproducibility | 项目归档 |

## 快速开始

### 使用 Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/your-org/AI-FanYi.git
cd AI-FanYi

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，修改必要的配置

# 3. 启动服务
docker-compose up -d

# 4. 初始化数据库
make db-upgrade

# 5. 查看日志
docker-compose logs -f api
```

### 使用 Make 命令

```bash
# 查看所有可用命令
make help

# 初始化项目
make init

# 构建并启动
make build
make up

# 运行测试
make test

# 代码检查
make lint
make format
```

### 访问服务

- **API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **MinIO 控制台**: http://localhost:9001 (minioadmin/minioadmin123)
- **Flower 监控**: http://localhost:5555 (需要启用 monitoring profile)

## 开发指南

### 环境要求

- Python 3.11+
- Docker & Docker Compose
- FFmpeg（如果本地开发）
- CUDA（如果使用 GPU Worker）

### 安装依赖

```bash
# 使用 pip
pip install -r requirements.txt

# 或使用 Make
make install
```

### 长期任务管理

对于需要长时间运行的编码任务，使用内置的进度管理系统：

```bash
# 开始新任务
make task-start TASK_ID=implement-m01

# 保存进度
make task-save PHASE=database-models MESSAGE="完成ORM模型"

# 查看状态
make task-status

# 恢复任务
make task-rescue

# 检查API额度
make task-quota
```

详见 [长期任务管理指南](docs/QUICK_START_TASKS.md)。

### 运行测试

```bash
# 所有测试
pytest

# 单元测试
make test-unit

# 集成测试
make test-integration

# 覆盖率报告
make test-coverage
```

### 代码质量

```bash
# 检查代码风格
make lint

# 自动格式化
make format
```

## 部署

### Docker 部署

```bash
# 生产环境构建
make prod-build

# 生产环境启动
make prod-up

# 启用 GPU Worker
make gpu-up

# 启用 Nginx 反向代理
make nginx-up
```

### 环境变量

关键环境变量（必须修改）：

```bash
# 数据库密码
POSTGRES_PASSWORD=your_secure_password

# MinIO 密钥
MINIO_SECRET_KEY=your_secure_key

# 应用密钥
SECRET_KEY=your_secret_key_here
```

完整配置见 `.env.example` 文件。

## 技术栈

### Layer 0
- **语言**: Python 3.11+
- **框架**: FastAPI
- **数据库**: PostgreSQL 15
- **缓存**: Redis 7
- **存储**: MinIO / S3
- **容器**: Docker + Docker Compose

### 媒体处理
- **音视频**: FFmpeg, PyAV, OpenCV
- **ASR**: Whisper, WhisperX
- **说话人识别**: Pyannote.audio

### AI/ML
- **翻译**: Qwen (本地 LLM)
- **TTS**: CosyVoice, F5-TTS

## 长期资产

平台真正积累的核心资产：

- **Character DB**: 人物知识库，跨集使用
- **Voice DB**: 声音配置库，保持音色一致
- **Story Bible**: 剧情数据库，保证剧情一致性
- **Translation Memory**: 翻译记忆库，术语统一
- **Artifact Library**: 工件库，可追溯
- **Workflow Library**: 工作流库，可复用

## 项目结构

```
AI-FanYi/
├── .github/
│   └── workflows/              # CI/CD 工作流
│       ├── ci.yml              # 主 CI 流程
│       └── release.yml         # 发布流程
├── docker/
│   ├── Dockerfile.api          # API 镜像
│   ├── Dockerfile.worker       # Worker 镜像
│   └── nginx.conf             # Nginx 配置
├── docs/
│   ├── adr/                   # 架构决策记录 (24 ADRs)
│   ├── DESIGN_INDEX.md         # 设计文档总览
│   └── agents/                # Agent 配置
├── scripts/                   # 脚本
│   ├── init.sh                # 初始化脚本
│   └── create-buckets.py      # MinIO 初始化
├── src/                       # 源代码（待实现）
├── tests/                     # 测试（待实现）
├── .dockerignore              # Docker 排除文件
├── .env.example               # 环境变量模板
├── docker-compose.yml         # Docker Compose 配置
├── Makefile                   # 便捷命令
├── requirements.txt           # Python 依赖
├── CLAUDE.md                  # Agent skills 配置
├── CONTEXT.md                 # 领域模型
└── README.md                  # 项目说明
```

## 文档

- [设计文档总览](docs/DESIGN_INDEX.md) - 完整的系统设计文档
- [领域模型](CONTEXT.md) - 核心概念和术语
- [Agent Skills](CLAUDE.md) - AI 助手配置

## 开发状态

### 设计阶段 ✅
- [x] 系统架构设计 (ADR 0001-0008)
- [x] 模块设计 (ADR 0009-0024)
- [x] 工程实践设计 (ADR 0012-0013)

### 配置阶段 ✅
- [x] Docker 配置
- [x] CI/CD 配置
- [x] 环境配置

### 实现阶段 🔄
- [ ] Layer 0 编排层
- [ ] M01-M14 各模块
- [ ] Web UI
- [ ] 测试覆盖

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 许可

待定

## 联系方式

- GitHub Issues: [https://github.com/your-org/AI-FanYi/issues](https://github.com/your-org/AI-FanYi/issues)
- Email: your-email@example.com

---

**设计文档**: [docs/DESIGN_INDEX.md](docs/DESIGN_INDEX.md) | **24 ADR 文档** | **完整模块设计**
