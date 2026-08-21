# Issue Tracker

## Provider

GitHub

## Repo

影视AI配音平台使用 stflj2022/-PDF- 仓库进行问题追踪。
主项目: stflj2022/-PDF-
备份: stflj2022/openclaw-backup

## Workflow

Issues are tracked in GitHub Issues at https://github.com/stflj2022/-PDF-/issues.

Use the `gh` CLI to interact with issues:
- `gh issue list` - list issues
- `gh issue create` - create a new issue
- `gh issue view <number>` - view an issue
- `gh issue close <number>` - close an issue

## Issue Structure

Issues use standard GitHub issues with labels for organization.

## Project Context

虽然仓库名为 -PDF-，实际项目为 **影视AI配音平台** - 一个模块化、可替换、可恢复的影视剧中文AI配音生产系统。

包含 14 个核心模块 + Layer 0 编排层：
- Layer 0: Orchestrator（总调度中心）
- M01: Project & Media Intake
- M02: Project Research & Identity Resolution
- M03: Subtitle & Dialogue Acquisition
- M04: Character Database Construction
- M05: Audio & Scene Analysis
- M06: Speaker → Character → Voice Identity
- M07: Subtitle / Dialogue Intelligence
- M08: Prosody & Performance Planning
- M09: Voice Synthesis
- M10: Dialogue Audio Processing & Scene Mixing
- M11: Video Assembly & Final Encoding
- M12: Project QA & Human Review
- M13: Batch / Season Pipeline
- M14: Project Archive & Reproducibility

## Wayfinding Operations

Wayfinder tickets are stored as GitHub issues with the following labels:
- `wayfinder:map` - for mapping/overview tickets
- `wayfinder:feature` - for feature tickets
- `wayfinder:bug` - for bug tickets
- `wayfinder:refactor` - for refactor tickets
- `wayfinder:tech-debt` - for technical debt tickets
- `layer:0` - Layer 0 编排层相关
- `module:m01-m14` - 各生产模块相关

Child tickets are linked via GitHub issue references and comments.

## Module Labels

- `module:m01` - 项目与媒体输入
- `module:m02` - 项目研究与身份解析
- `module:m03` - 字幕与对白获取
- `module:m04` - 人物数据库构建
- `module:m05` - 音频与场景分析
- `module:m06` - 说话人→人物→音色身份
- `module:m07` - 字幕/对白智能
- `module:m08` - 韵律与表演规划
- `module:m09` - 语音合成
- `module:m10` - 对白音频处理与场景混音
- `module:m11` - 视频组装与最终编码
- `module:m12` - 项目质检与人工审查
- `module:m13` - 批量/季集流水线
- `module:m14` - 项目归档与可复现性
