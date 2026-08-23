# laobai.mp4 完整流程运行报告 + Web UI 部署记录

> 日期：2026-08-23
> 范围：`测试视频/laobai.mp4`（15 秒短视频）跑通 **Layer 0 + M01~M14** 全流程，并部署可访问的 Web UI。

---

## 一、目标

按《计划书/ai-fanyi-00-2-冻结版layer 0.txt》与《ai-fanyi-00-1-影视AI配音平台简介.txt》的架构，验证整条**面向影视剧的中文 AI 配音生产流水线**：

- **Layer 0 = Workflow Orchestrator**，不直接做 ASR/翻译/TTS/克隆，而是判断、编排、调度、缓存、资源管理和恢复。
- M01~M14 各自承担具体能力，模块之间通过 Artifact 传递数据。
- 附带把 Web 控制界面（React 前端 + FastAPI 后端）真正跑起来。

---

## 二、完整流程产出

| 产物 | 路径 | 说明 |
|------|------|------|
| 最终配音视频 | `输出视频/final_dubbed.mp4` | 15.06s, h264+aac 48kHz, 4.4MB |
| 封装版 | `输出视频/final_encapsulated.mp4` | 15.07s, 4.2MB |
| 项目归档 | `projects/proj_64007428ffb6/archive/proj_64007428ffb6.zip` | 实际为 `.tar.gz`（ArchiveModule 生成 tar.gz） |
| 人物数据库 | `projects/proj_64007428ffb6/dialogue/character_db.json` | 角色"老白"，voice_laobai，含 .spk/.rvq 特征 |
| 合成语音 | `projects/proj_64007428ffb6/dialogue/synth/d*.wav` | 5 句中文对白 |
| 混音段 | `projects/proj_64007428ffb6/dialogue/mix/m*.wav` | loudnorm 归一化后 |
| 各模块 manifest | `projects/proj_64007428ffb6/manifests/ctx_M*.json` | M01~M14 每阶段产物 + job 状态 |

### 每模块实际后端

| 模块 | 能力 | 实际执行后端 |
|------|------|--------------|
| M01 | Project & Media Intake | `MediaIntakeWorker`（ffprobe 探针 + 入库）|
| M02 | Media / Scene Analysis | htdemucs 分离人声 |
| M03 | Subtitle Acquisition | SubtitleRunner（laobai 无现成字幕，标记为空，对白由 M05 转写构建）|
| M04 | Character Database + 克隆 | qwen-codec 提取 .spk/.rvq 语音特征 |
| M05 | Audio & Scene 分析 | faster-whisper-large-v3 转写（5 段英文对白）|
| M06 | Speaker→Character | SpeakerToCharacterMapper -> 全部映射"老白" |
| M07 | 对白智能 + 翻译 | ollama `gemma4-e2b` 翻译为中文 |
| M08 | 韵律/表演规划 | ProsodyPlanner |
| M09 | 语音合成 | qwen-tts（qwentts C++ `qwen-tts` CLI + 老白克隆特征）|
| M10 | 音频混音 | loudnorm 音量归一化(≤-16 LUFS) + 时间轴放置 |
| M11 | 视频组装 | VideoAssembler（adelay+amix 混音、替换音轨、嵌入字幕）|
| M12 | 视频封装 | VideoEncapsulationWorker |
| M13 | QA | QAChecker —— **评分 100** |
| M14 | 归档 | ArchiveModule（tar.gz + manifest + 校验）|

**完整流程运行：`python3 scripts/run_full_pipeline.py`**，支持 `--project <id>` 断点续跑、`--reset`。

---

## 三、遇到的问题与修复

### 1. 配音视频"只有画面和滋滋声"（关键质量问题）

**现象**：最终视频音频几乎静音/失真，频谱检测无有效人声。

**根因**：`run_cli_tts` 里给 qwen-tts 传了 `--greedy`（贪婪采样）。qwen-talker 在贪婪采样下对"老白"克隆特征合成中文时**发散为空/噪声输出**（生成帧数异常、音量低至 -55dB）。

**修复**：
- 去掉 `--greedy`，改用默认随机采样 + `--max-new` 上限（防无限生成）。
- 合成后做**音量校验**（volumedetect mean > -40dB 才算有效），失败用不同 `--seed` 重试，最多 4 次。
- 老白音色（英文参考）合成中文电平偏低，混音时用 `loudnorm` 拉平音量。

**验证**（客观频谱判据，低频占比 0.5+ 视为人声而非白噪声）：
- 5 个混音段均判定为"人声/语音"，重心 1119~2113Hz，低频占比 0.59~0.81。
- 最终视频音频 `LRA -25.7 ~ -16.5 LUFS`（正常语音电平）。

### 2. 各模块运行期 bug（为让系统真正可跑的必要修复）

| 文件 | 问题 | 修复 |
|------|------|------|
| `src/filmdub/adapter/voice.py` | M09 的 qwen-tts 后端与 C++ qwen-tts server 不兼容 | OpenAI 分支补 `language`/`response_format`，输出 `.wav` |
| `src/filmdub/workers/qa/worker.py` | ffprobe 的 sample_rate/channels 是字符串，与 int 比较崩溃 | 转 int 容错解析 |
| `src/filmdub/workers/qa/models.py` | `QAResult.success`/`overall_score` 无默认值，check() 主路径构造报错 | 加默认值 |

修复后通过 97 个相关单测。

---

## 四、Web UI 部署

Web UI（React 17/18 + Antd + React Router + React Query + Zustand）前端代码本就存在，本次补齐后端托管的整条链路：

1. **前端构建**：`npm install` + `npm run build` → `apps/web/dist/`（因家目录只读，npm cache 指到工作区内 `apps/web/npmcache`，已 `gitignore`）。
2. **后端静态托管**：`apps/api/main.py` 新增 `_mount_web_ui()`——挂载 `/assets` + catch-all SPA fallback；lifespan 里 `init_db()` 建 orchestrator 库表。
3. **WebSocket 协议对齐**：前端原用 `socket.io-client`，后端是原生 WebSocket `/ws`，协议不匹配。将 `apps/web/src/services/websocket.ts` 重写为**原生 WebSocket**（JSON 文本帧 + 事件分发），接口保持不变；验证 `ping→pong` 互通。

### 访问方式

- 后端 + Web UI：`http://localhost:8000/`
  - SSH：`python3 -m uvicorn filmdub.apps.api.main:app --host 0.0.0.0 --port 8000`
  - Docker：`make up` / `make up-api up-web`
- API 文档：`http://localhost:8000/docs`
- WebSocket：`ws://localhost:8000/ws`

### 验证结果

| 端点 | 结果 |
|------|------|
| `/health` | `{"status":"healthy","version":"0.1.0"}` |
| `/` | 返回 `index.html`（title "AI-FanYi - 影视AI配音平台"）|
| `/assets/index-*.js` | 200 text/javascript |
| `/projects`、`/workers`（SPA 路由）| 200（fallback 到 index.html）|
| `/api/v1/projects` | 返回 laobai 项目（status=completed）|
| `/ws`（原生 WS）| connected → ping → pong |

> 注：laobai 流程项目以 UUID 注册到 orchestrator 库（orchestrator 主键为 UUID，流程内部 id 为 `proj_xxx` 字符串，二者在 orchestrator 项目记录里通过 description 关联）。

---

## 五、产物与运行说明

### 快速查看配音视频

```bash
# 已在项目根目录
ls 输出视频/
# final_dubbed.mp4       已修复的中文配音视频（真实语音）
# final_encapsulated.mp4 封装版
```

### 重跑完整流程（Layer0 + M01~M14）

```bash
python3 scripts/run_full_pipeline.py            # 全新项目全流程
python3 scripts/run_full_pipeline.py --project proj_xxx   # 断点续跑
```

### 外部服务依赖

| 服务 | 地址 | 用途 |
|------|------|------|
| qwen-tts（qwentts C++）| 启动 `~/桌面/qwentts/启动WebUI.sh`（tts-server 常驻 8081，CLI 用时无需常驻）| M04 克隆 / M09 合成 |
| ollama `gemma4-e2b` | `http://localhost:11434` | M07 中文翻译 |
| faster-whisper-large-v3 / htdemucs | 本地缓存（HuggingFace）| M02/M05 |

> 关键提示：合成中文用**老白（英文参考）音色**发音正常但电平略暗；若更在意音色质感，可在 qwentts WebUI 里用**中文参考**克隆音色再替换 `run_full_pipeline.py` 中的 `voice.spk/rvq` 路径。

---

## 六、后续建议（超出本次范围）

- **归档扩展名**：`ArchiveModule` 实际生成 `tar.gz`，可将输出名统一为 `.tar.gz` 以符合直觉。
- **合成时长对齐**：当前混音把合成语音按时间槽放置（`adelay`）但未裁剪超出部分，长句可能溢出下一发音区。可在 M09 用 `--max-new` 按目标时长进一步限制，或在 M10 对超长段做 `apad/atrim`。
- **QA 接入真实对白**：M13 目前只做技术质量检查，可把 `dialogue_timeline` 传入做配音一致性/翻译质量评分。
- **M03 字幕**：laobai 无现成字幕；若接入真实剧集，用 `测试视频/字幕/` 里的 ASS 字幕源可走通 M03 完整路径。
