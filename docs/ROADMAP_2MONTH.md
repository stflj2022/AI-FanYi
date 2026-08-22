# AI-FanYi 影视 AI 配音平台 — 2 个月实施路线图
**版本**: V1.0 | **启动**: 2026-08-23 | **周期**: 8 周（≥2 个月）
**模式**: 无人值守自动推进（开机自启 + systemd + 只非高峰用 Zai glm-4.7）

---

## 0. 总目标

把 qwentts 深度集成进 AI-FanYi 14 模块流水线，实现「**外国人本人音色说中文**」：
- **强替换** M09（语音生成）+ M04（声音数据库）
- **辅助替换** M02（音频分析）+ M05（ASR 转写）
- **弱整合** M10（韵律）
- 其余模块（M01/M03/M06/M07/M08/M11/M12/M13/M14）补全实现
- Layer 0 编排器统一调度，输出可观看的中文配音视频

---

## 1. 阶段划分与里程碑

### 阶段 0：基础设施（本周，第 0-3 天）
- [ ] 建 `.venv` + 装依赖（AI-FanYi + qwentts requirements）
- [ ] 确认 zai glm-4.7 可用 + 非高峰时段调度 + 额度耗尽等待
- [ ] qwentts 自启（已有 `qwen-tts.service`）+ 验证接口连通
- [ ] 开机自启 systemd（`aifanyi-driver.service` + watchdog）
- [ ] **验收**：`qwen-tts.service` 运行中，driver 开机自跑，短视频端到端首次连通

### 阶段 1：Layer 0 + qwentts 集成（第 1-2 周）
- [ ] Layer 0 Orchestrator 完整实现（Task Context→Asset Discovery→Capability Matrix→Workflow Selector→Dependency Resolver→Planner→Executor）
- [ ] qwentts 适配器层（统一接口，供 M04/M09/M02/M05 调用）
  - `adapter/voice.py`（克隆/生成/列出音色）
  - `adapter/asr.py`（转写）
  - `adapter/separate.py`（人声分离）
- [ ] M02 音频分析：接入 HTDemucs 分离（人声/背景/环境音）
- [ ] M05 ASR：接入 Faster-Whisper large-v3 转写
- [ ] M04 声音数据库：`cloned_voices/` 作为音色库
- [ ] M09 语音合成：接入 qwen-tts server 批量生成
- **验收**：短视频(laobai/pingi)跑通「分离→转写→克隆→合成」端到端

### 阶段 2：理解层模块（第 3-4 周）
- [ ] M03 人物数据库（人物识别、人脸/角色追踪）
- [ ] M06 翻译（中文化对白，Qwen 或 API）
- [ ] M07 说话人→人物映射（把 ASR 说话人聚类匹配到人物库）
- **验收**：长片片段级「识别人物→分配音色→翻译」正确

### 阶段 3：表演层模块（第 5-6 周）
- [ ] M08 对白准备（文本清洗、时长预算、断句）
- [ ] M10 韵律/表演处理（语速、停顿、情绪——qwentts 弱整合）
- [ ] M11 音频混音（AI对白+背景乐+环境音+音效）
- **验收**：一段对白带情绪/停顿，混音无原声残留

### 阶段 4：组装层模块（第 7 周）
- [ ] M12 视频封装（中文对白+背景+字幕 → mp4）
- [ ] M13 QA（技术/配音质量自动检查，生成 QA Report）
- [ ] M14 归档（人物/声音/剧情/翻译记忆/Artifact/模型版本全保存）
- **验收**：输出完整 QA 通过的中文配音视频

### 阶段 5：长片全流程 + 打磨（第 8 周）
- [ ] 用《绝命毒师》长片全流程验证
- [ ] 音色一致性、情绪、音量统一优化
- [ ] 最终交付：可直接观看的中文配音视频 + 完整归档

---

## 2. 每日运行节奏（无人值守）

```
开机自启 → systemd 启动 driver
driver 判断: 当前非高峰?(工作日14-18之外) && zai额度可用?
  是 → 用 zai glm-4.7 跑一张工单 → pytest 验收 → commit+push → 下一张
  否 → 休眠等待(高峰结束 / 额度重置/5h) → 恢复
每完成 3 张工单 → code-review 检查并修复
工单连续失败 3 次 → 标记 blocked + 记录原因，换下一张
```

**Provider 策略**：
- 默认只用 `zai-coding-cn/glm-4.7`
- 非高峰时段（工作日 14:00-18:00 之外）才运行
- zai 额度耗尽（每 5 小时重置）→ 等待重置后继续
- **临时 deepseek 开关**（`TEMP_DEEPSEEK` 标志）：zai 未重置时临时用 deepseek 推进，重置后切回

---

## 3. 测试与验收

- 每模块：单元测试 + 实例测试（短视频快速跑通）
- 阶段里程碑：长片片段级全流程验证
- 最终：长片全流程 + QA 通过
- 测试视频：`测试视频/laobai.mp4`、`pingi.mp4`（短）；`绝命毒师...mkv`（长，最终验证）

---

## 4. 模型/文件下载策略

- 自动下载尝试 **5 次**；失败后写入日志并在仓库留下提示文件，给出手动下载地址：
  - HTDemucs: https://github.com/facebookresearch/demucs
  - Faster-Whisper large-v3: https://huggingface.co/Systran/faster-whisper-large-v3
  - qwen-tts GGUF: https://github.com/ServeurpersoCom/qwentts.cpp
- 下载文件位置：`.unattended/models/` 或项目 `models/` 目录

---

## 5. 风险与对策

| 风险 | 对策 |
|------|------|
| zai 高峰/额度不可用 | 非高峰调度 + 额度等待 + 临时 deepseek |
| 断电/关机 | systemd 自启 + 状态落盘 + RECOVERY 恢复 |
| 模型下载慢/失败 | 5 次自动重试 + 手动下载提示 |
| 测试环境损坏 | pytest 独立验收 + 失败打回 |
| 上下文膨胀 | 每 8 轮换新会话 + RECOVERY.md |
| qwentts server 挂 | qwen-tts.service Restart=always + 探活重启 |
