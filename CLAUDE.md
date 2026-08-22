# AI-FanYi - 影视 AI 配音平台

## Agent Skills

This project uses Matt Pocock's engineering skills. Configuration lives in `docs/agents/`:

- **Issue Tracker**: `docs/agents/issue-tracker.md` - GitHub issues at stflj2022/-PDF-
- **Triage Labels**: `docs/agents/triage-labels.md` - Five canonical triage labels for issue classification
- **Domain Docs**: `docs/agents/domain.md` - Single-context layout with CONTEXT.md and docs/adr/

## Project Description

模块化、可替换、可恢复的影视剧中文 AI 配音生产系统。

本平台是一套完整的影视后期生产流水线，使没有中文配音的影视剧能够经过自动化处理，最终得到人物身份稳定、音色基本一致、中文表达自然、语速与画面基本同步、情绪基本符合剧情、整体音量统一的中文配音视频。

## System Architecture

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

## Module List

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

## Core Goals

- **人物身份稳定**: 同一人物跨集、跨季音色一致
- **音色基本一致**: AI 配音尽量接近原演员声音特征
- **中文表达自然**: 翻译和配音符合中文表达习惯
- **语速与画面同步**: 对白时间轴与视频匹配
- **情绪符合剧情**: 配音情绪与剧情场景一致
- **整体音量统一**: 符合广播标准

## Technology Stack

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

## Project Structure

```
AI-FanYi/
├── src/
│   └── filmdub/
│       ├── core/              # 核心模块（配置、数据库、模型）
│       ├── apps/
│       │   ├── api/           # FastAPI 后端
│       │   └── web/           # 前端界面
│       └── workers/           # 各模块 Worker
│           ├── media_intake/  # M01
│           ├── research/      # M02
│           ├── subtitle/      # M03
│           ├── character_db/  # M04
│           └── ...
├── tests/                     # 测试套件
├── docs/
│   ├── adr/                   # 架构决策记录
│   └── agents/                # Agent 技能配置
├── data/projects/             # 项目数据
├── docker/                    # Docker 配置
├── scripts/                   # 脚本工具
├── CLAUDE.md                  # 本文件
├── CONTEXT.md                 # 领域模型
└── README.md                  # 项目说明
```

## Development Workflow

使用 Matt Pocock 的工程技能进行开发：

1. **grill-me / grill-with-docs**: 开工前质询，澄清设计细节
2. **to-spec**: 大任务生成规范文档
3. **to-tickets**: 分解为具体任务 tickets
4. **implement**: 执行实现（自动处理阻塞关系）
5. **code-review**: 双轴代码审查（标准+规范）

## Available Skills

项目配置了以下 Agent 技能：

### 核心工程技能
- `grill-me` - 激进的面试式质询
- `grill-with-docs` - 质询并生成文档
- `to-spec` - 生成规范文档
- `to-tickets` - 分解为任务 tickets
- `implement` - 执行实现
- `code-review` - 双轴代码审查

### 辅助技能
- `triage` - 问题分流
- `domain-modeling` - 领域建模
- `research` - 研究任务
- `prototype` - 快速原型
- `tdd` - 测试驱动开发
- `diagnosing-bugs` - Bug 诊断
- `resolving-merge-conflicts` - 合并冲突解决

## Long-term Assets

平台真正积累的核心资产：

- **Character DB**: 人物知识库，跨集使用
- **Voice DB**: 声音配置库，保持音色一致
- **Story Bible**: 剧情数据库，保证剧情一致性
- **Translation Memory**: 翻译记忆库，术语统一
- **Artifact Library**: 工件库，可追溯
- **Workflow Library**: 工作流库，可复用

## Quick Start

```bash
# 查看可用模型
pi --list-models

# 启动开发流程
/grill-me

# 生成规范
/to-spec

# 分解任务
/to-tickets

# 执行实现
/implement

# 代码审查
/code-review main
```

## Documentation

- [设计文档总览](docs/DESIGN_INDEX.md)
- [领域模型](CONTEXT.md)
- [架构决策记录](docs/adr/)
- [Issue Tracker 配置](docs/agents/issue-tracker.md)
- [Domain 文档配置](docs/agents/domain.md)
