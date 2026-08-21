# Domain Documentation

## Layout

Single-context layout:

- `CONTEXT.md` - Domain model and shared vocabulary at the root
- `docs/adr/` - Architecture Decision Records

## CONTEXT.md

The `CONTEXT.md` file contains:
- Domain model and key terminology for 影视AI配音平台
- Layer 0 (Orchestrator) 概念
- 14 个生产模块 (M01-M14) 定义
- Artifact、Project、Job、Workflow 等核心概念
- Character DB、Voice DB、Story Bible、Translation Memory 等长期资产
- 模块间数据流

This file is actively maintained by the `domain-modeling` skill as terms and concepts are resolved.

## ADRs

Architecture Decision Records are stored in `docs/adr/`.
Each ADR captures a significant architectural decision, its context, and consequences.

ADRs are created by the `domain-modeling` skill when architectural decisions are made.

## Key Domain Concepts

### Layer 0
总调度中心，不直接进行媒体处理，负责编排、调度、资源管理。

### Module
M01-M14 生产模块，通过 Artifact 传递数据。

### Artifact
模块之间的标准接口，存储在 Artifact Registry 中。

### Character DB
人物数据库，跨集、跨季持续使用的长期资产。

### Voice Profile
人物的声音配置，包含 TTS 模型和参数。

### Dialogue
一句需要配音的台词，包含文本、时间码、说话人、情绪等。

### Project / Job
Project 是完整的配音工程，Job 是其中的处理单元（通常一集）。
