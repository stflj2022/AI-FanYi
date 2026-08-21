# 影视 AI 配音平台 - 领域模型

## 系统概述

**影视AI配音平台** 是一个模块化、可替换、可恢复、面向整部影视剧生产的 AI 配音平台。

**目标**: 将没有中文配音的影视剧，经过自动化处理，得到人物身份稳定、音色基本一致、中文表达自然、语速与画面基本同步、情绪基本符合剧情、整体音量统一的中文配音视频。

---

## 核心概念

### Layer 0 (Orchestrator)

**总调度中心**。不直接进行 ASR、翻译、TTS 或视频处理。

**职责**:
- 创建项目和作业
- 管理工作流、状态、调度
- 管理 Artifact
- 管理 GPU/CPU 资源
- 启动和销毁 Worker
- 失败检测和自动重试
- 断点恢复
- 日志和状态监控
- Web UI
- 项目级数据库调用
- 最终归档

**类比**: 影视 AI 配音厂的"总导演 + 制片主任 + 调度中心"

---

### Module (生产模块)

**M01-M14** 是真正执行影视处理工作的生产模块。

模块之间通过 **Artifact** 传递数据，不直接互相调用。

#### 模块列表

| 模块 | 名称 | 核心职责 |
|------|------|----------|
| M01 | Project & Media Intake | 项目建立、媒体输入、获取元数据 |
| M02 | Project Research & Identity Resolution | 媒体分析、场景分析、时间轴 |
| M03 | Subtitle & Dialogue Acquisition | 字幕获取、对白切分 |
| M04 | Character Database Construction | 人物数据库构建 |
| M05 | Audio & Scene Analysis | 音频分析、说话人识别 |
| M06 | Speaker → Character → Voice Identity | 说话人到人物到音色的映射 |
| M07 | Subtitle / Dialogue Intelligence | 字幕/对白智能处理 |
| M08 | Prosody & Performance Planning | 韵律与表演规划 |
| M09 | Voice Synthesis | AI 语音合成 |
| M10 | Dialogue Audio Processing & Scene Mixing | 对白音频处理与场景混音 |
| M11 | Video Assembly & Final Encoding | 视频组装与最终编码 |
| M12 | Project QA & Human Review | 项目质检与人工审查 |
| M13 | Batch / Season Pipeline | 批量/季集流水线 |
| M14 | Project Archive & Reproducibility | 项目归档与可复现性 |

---

### Artifact

**模块之间的标准接口**。

模块之间不直接互相调用，而是通过 Artifact Registry 传递数据。

**示例**: M08 生成 `dialogue.json` 作为 Artifact，M09 从 Artifact Registry 读取它。

**好处**: M09 不需要知道 M08 是什么技术实现。

---

### Project (项目)

**一个完整的配音工程**，对应一部电视剧、一季或一集。

**包含**:
- 原始视频
- 字幕
- 剧名、季数、集数
- 语言
- 元数据 (TMDB/IMDb)

---

### Job (作业)

**Project 中的一个处理单元**。

通常对应一集电视剧的处理。

---

### Workflow (工作流)

**定义 Module 的执行顺序和依赖关系**。

是一个 DAG (有向无环图)，而非简单的线性流程。

---

### Character DB (人物数据库)

**平台最重要的长期资产之一**。

**记录**:
- Character ID
- 人物姓名、别名
- 性别、年龄段
- 身份、人物关系
- 人物背景
- 演员
- 首次出现集数
- 人物描述
- 说话特点
- 语言特点

**意义**: 跨集、跨季持续使用，避免每一集重新"认识"人物。

---

### Voice Profile (音色档案)

**Character 的声音配置**。

**记录**:
- 原演员声音特征
- 音色、音高、语速
- 声音年龄、强度
- 情绪范围
- 声音参考片段
- Voice ID
- TTS 模型
- Voice Clone 参数
- 参数版本

**示例**: Walter → VOICE-WALTER-V05

---

### Voice DB (声音数据库)

**所有 Voice Profile 的集合**。

---

### Story Bible (剧情数据库)

**电视剧的剧情知识库**。

记录人物关系、剧情发展、重要事件等，用于保证翻译和配音的剧情一致性。

---

### Translation Memory (翻译记忆库)

**跨集、跨季的翻译记忆**。

保证:
- 人名统一
- 专有名词统一
- 人物语气统一
- 前后剧情一致
- 俚语合理翻译
- 称呼一致

---

### Dialogue (对白)

**一句需要配音的台词**。

**包含**:
- 文本
- 时间码 (开始/结束)
- 说话人 (Speaker)
- 对应人物 (Character)
- 音色 (Voice Profile)
- 情绪
- 语速
- 停顿

---

### Speaker (说话人)

**音频中的说话人标识**。

由 ASR + Speaker Diarization 识别得出，需要映射到 Character。

---

### Character (人物)

**电视剧中的角色**。

由 Character DB 管理，有唯一的 Character ID。

---

### Scene (场景)

**视频中的一个场景**。

包含镜头、时间范围、对白等信息。

---

### Dialogue Timeline (对白时间轴)

**所有对白的时间排列**。

包含每句对白的时间码、说话人、文本等。

---

### QA Report (质检报告)

**自动质量检查的结果**。

包含:
- 技术质量检查
- 配音质量检查
- 问题列表

---

## 模块间数据流

```
M01 (Project Intake)
  → Project Metadata, Media Manifest, Source Video, Subtitle

M02 (Media Analysis)
  → Media Analysis, Scene Timeline, Audio Analysis

M03 (Subtitle Acquisition)
  → Subtitle, Dialogue Timeline

M04 (Character DB)
  → Character Database

M05 (Audio Analysis)
  → Speaker Embeddings, Audio Features

M06 (Speaker → Character)
  → Dialogue with Speaker/Character mapping

M07 (Dialogue Intelligence)
  → Processed Dialogue, Emotion Tags

M08 (Prosody Planning)
  → Dialogue with TTS Parameters

M09 (Voice Synthesis)
  → Generated Audio Files

M10 (Audio Processing & Mixing)
  → Mixed Audio Tracks

M11 (Video Assembly)
  → Final Video with Chinese Audio

M12 (QA)
  → QA Report

M13 (Batch/Season)
  → Batch Processing Results

M14 (Archive)
  → Project Archive
```

---

## 长期资产

**平台真正积累下来的不是视频，而是**:

1. **Character DB** - 人物知识库
2. **Voice DB** - 声音配置库
3. **Story Bible** - 剧情知识库
4. **Translation Memory** - 翻译记忆库
5. **Artifact Library** - 工件库
6. **Workflow Library** - 工作流库

这些资产决定了平台能否从"单集 AI 配音工具"升级成"真正能够连续制作整部电视剧的 AI 配音系统"。

---

## 技术栈 (不属于领域模型，仅供参考实现)

**Layer 0**: Python, FastAPI, PostgreSQL, Redis, Docker, React

**ASR/对齐**: Whisper, WhisperX

**Speaker Diarization**: Pyannote.audio

**翻译**: Qwen (本地 LLM)

**TTS**: CosyVoice, F5-TTS, XTTS (可替换)

**音视频**: FFmpeg, PyAV, OpenCV
