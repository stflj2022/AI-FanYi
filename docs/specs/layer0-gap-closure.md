# Layer 0 动态工作流引擎与差距补齐 规范文档

**创建日期**: 2026-08-24
**状态**: Approved
**相关计划**: 
- `/home/wu/桌面/AI-FanYi/计划书/ai-fanyi-00-1-影视AI配音平台简介.txt`
- `/home/wu/桌面/AI-FanYi/计划书/ai-fanyi-00-2-冻结版layer 0.txt`

---

## Problem Statement

对照两份计划书评估后，AI-FanYi 平台存在以下主要差距（按优先级）：

### P0-1: Layer 0 动态工作流引擎缺失（计划书 2 核心）
当前平台是"手动顺序流水线 + Job 依赖调度"（`run_full_pipeline.py` 顺序执行 exec_M01..M14 + `scheduler.py` 任务调度），**未实现计划书 2 冻结版的七阶段动态工作流编排**：
- Task Context / Asset Discovery / Capability Matrix / Workflow Selector（QUICK/STANDARD/PRODUCTION）/ Dependency Resolver / Workflow Planner（RUN_FULL/RUN_INCREMENTAL/LOAD/SKIP）/ Executor

### P0-2: Story Bible（剧情数据库）未实现
计划书反复强调的核心长期资产，用于保证剧情一致性、翻译上下文、人物语气统一。

### P1-3: M10 独立模块缺失
计划书要求 M10（音色/韵律/表演处理）独立于 M09（TTS），"谁在说 vs 像人在说"分离。当前相关处理内嵌于 M09/M08。

### P1-4: M11 完整混音缺失
计划书要求 M11 混合 AI 对白 + 背景音乐 + 环境音 + 音效。当前仅单层对白 amix。

### P1-5: worker→DB 持久化未打通
M03/M04/M05 等 worker 产出不写入 orchestrator 数据库表（characters/voice_profiles 等），长期资产无法跨集跨季复用。

### P2-6: M13 QA / M02 场景检测 / TTS Adapter 统一
- M13 QA 缺 LUFS/静音/爆音/漏台词检测，不写 QA 报告
- M02 缺场景/镜头/黑屏检测
- TTS 双路径（Qwen Adapter vs CosyVoice/F5 直接调用）未统一

---

## 目标

按计划书 2 的 10 条工程原则，实现**状态空间 + 能力矩阵 + 依赖图 + 动态计划生成**的 Layer 0 工作流引擎，并补齐上述全部差距。

## 技术方案

### 1. Layer 0 工作流引擎（P0-1）

新增 `src/filmdub/orchestrator/workflow/` 子包，实现七阶段：

| 组件 | 职责 | 关键输出 |
|------|------|----------|
| `task_context.py` | 构建 TaskContext（项目/媒体/字幕/人物库/声音库/质量要求） | TaskContext dict |
| `asset_discovery.py` | 检查资源状态（视频/音频/字幕/DB/Artifact） | AssetStatus |
| `capability_matrix.py` | 资源能力判定（NONE/PARTIAL/COMPLETE/INVALID/OUTDATED） | CapabilityMatrix |
| `workflow_selector.py` | 规则引擎选择 QUICK/STANDARD/PRODUCTION（第一版不用 LLM） | WorkflowType |
| `dependency_resolver.py` | 根据能力矩阵动态解析模块前置依赖 | DependencyGraph |
| `workflow_planner.py` | 生成执行计划（RUN_FULL/RUN_INCREMENTAL/LOAD/SKIP） | ExecutionPlan |
| `workflow_executor.py` | 执行计划（复用现有 scheduler DispatchEngine） | 执行结果 |

同时提供 7 种工作流类型配置（QUICK/STANDARD/PRODUCTION/PREVIEW/REVOICE/RERENDER/QA_ONLY），存放 `layer0/workflows/*.yaml`。

### 2. Story Bible（P0-2）

- `src/filmdub/core/models/` 增加 StoryEntry 模型（项目/角色/事件/关系/时间线/状态）
- `src/filmdub/workers/story_bible/` 新 worker：从剧本/字幕/人物库自动提取剧情条目
- 接入 M06 翻译上下文（Qwen 翻译 prompt 携带剧情上下文）

### 3. M10 独立模块（P1-3）

- `src/filmdub/workers/prosody_performance/` 新 worker（M10Worker）
- 从 voice_synthesis 分离音高/语速/停顿/情绪/强弱/呼吸/音量/韵律处理
- 输入：M09 TTS 原始音频 + M08 韵律计划；输出：表演化处理后的音频

### 4. M11 完整混音（P1-4）

- 增强 `video_assembly` 混音逻辑：AI 对白 + 原声分离（adapter/separate.py htdemucs）+ 背景音乐 + 环境音 + 音效
- 音量统一（LUFS/EBU R128）

### 5. worker→DB 持久化（P1-5）

- M03/M04/M05 worker 产出写入 orchestrator 的 characters/voice_profiles/audio_analysis 表
- 提供跨集复用的查询接口

### 6. QA / M02 / TTS Adapter（P2-6）

- M13 QA：增加 LUFS 响度/静音/爆音/漏台词检测，输出 QA 报告文件
- M02：场景/镜头/黑屏检测（基于 FFmpeg/PyAV 场景切割）
- TTS Adapter：CosyVoice/F5-TTS 统一并入 `adapter/voice.py` Adapter 接口

## 验收标准

1. `python -m pytest tests/` 全绿
2. `run_full_pipeline.py` 可基于新引擎动态生成最小执行链（不同输入状态产生不同执行计划）
3. 能力矩阵/选择器/规划器有单元测试覆盖
4. Story Bible 有模型 + worker + 翻译上下文接入
5. M10 独立 worker 存在且测试通过
6. M11 混音含多音轨（对白+音乐+环境音）
7. character/voice_profiles 表由 worker 写入
8. 所有新功能通过双遍 code-review

## 相关文档

- 冻结版 Layer 0: `/home/wu/桌面/AI-FanYi/计划书/ai-fanyi-00-2-冻结版layer 0.txt`
- 平台简介: `/home/wu/桌面/AI-FanYi/计划书/ai-fanyi-00-1-影视AI配音平台简介.txt`
