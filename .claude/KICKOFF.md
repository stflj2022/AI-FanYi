# 开工提示词 — AI-FanYi 剩余全部工作

你是本仓库的自主开发工程师，目标：完成影视AI配音平台剩余全部工作（Layer 0 编排器、M02-M14、Web 前端），深度集成 qwentts 实现「外国人本人音色说中文」。

## 必读（按序）
1. CLAUDE.md、CONTEXT.md —— 领域模型与规范
2. docs/ROADMAP_2MONTH.md —— **2 个月实施路线图（阶段划分、里程碑、验收标准，按此推进）**
3. docs/adr/ —— 架构决策，遇到分歧以 ADR 为准
4. MIGRATION.md —— 已迁移的 M01-M03（src/filmdub/workers/{media_intake,research,subtitle}）
5. docs/QUICK_START_TASKS.md、docs/RESUME_STRATEGY.md
6. 计划书/ —— 00-1 平台简介、00-2 Layer 0 方案、各模块计划书（02-14 的实现依据）

## qwentts 集成要点（本工程核心）
qwentts 位于 `~/桌面/qwentts/`，已作为 systemd `qwen-tts.service` 开机自启（tts-server 运行中）。
**首选实现依据**：`docs/adapter-design.md`（Layer 0 adapter 接口设计）——按 §11 实现顺序，先建 `src/filmdub/adapters/` 契约，再逐 adapter 实现+测试。
集成映射：
- **强替换 M09（语音生成）**：调 qwen-tts server 批量合成 → 用 `cloned_voices/` 音色
- **强替换 M04（声音数据库）**：qwentts 音色克隆（参考音频+文本→.spk/.rvq→注册）作为音色库
- **辅助替换 M02（音频分析）**：HTDemucs 人声/背景分离
- **辅助替换 M05（ASR 转写）**：Faster-Whisper large-v3 转写
- **弱整合 M10（韵律）**：语速/停顿等基础控制
实现方式：建 **adapter 层**（`src/filmdub/adapters/{voice,asr,separate}.py`）统一封装 qwentts 接口，各 worker 只依赖 adapter，不直接耦合 qwentts。

## 工作流
1. 若 specs/ 不存在：用 to-spec 技能从上述文档产出 specs/
2. 用 to-tickets 把 spec 拆为工单写入 docs/tickets/*.md，每个工单含「状态: todo|doing|done|blocked」字段和依赖关系
3. 实施循环：取一个未阻塞的 todo 工单 → implement → 测试通过 → git commit（格式 `feat(Mxx): 描述`）→ 更新工单状态为 done → 每 3 个工单用 code-review 检查一次并修复问题
4. 测试连续失败 3 次 → 工单标记 blocked 并写明原因，换下一个
5. ADR 未覆盖且影响架构的决策 → 先写 ADR 草案再继续，不要停下来问

## 测试命令（固定，驱动会用此命令独立验收）
```
cd ~/桌面/AI-FanYi && .venv/bin/python -m pytest src/filmdub/tests/ -q
```
- 每个新功能必须配测试
- 实例测试用 `测试视频/laobai.mp4`、`pingi.mp4`（短视频快速跑通）；长片《绝命毒师》用于最终全流程

## 模型下载策略
自动下载模型/文件尝试 **5 次**；失败后在仓库留 `docs/MANUAL_DOWNLOAD.md`，给出手动下载地址：
- HTDemucs: https://github.com/facebookresearch/demucs
- Faster-Whisper large-v3: https://huggingface.co/Systran/faster-whisper-large-v3
- qwen-tts GGUF: https://github.com/ServeurpersoCom/qwentts.cpp

## 硬约束
- 任何时刻都不要停下来提问或等待确认；拿不准就按 ADR/惯例自主决策并直接执行
- 不改变 src/filmdub 已验证代码（M01-M03）的对外行为，只做集成所需适配
- 每个 commit 后立即 `git push`（远程已配 SSH，可直接推）
- 每轮结束确保 git 工作区干净（全部提交）
- 全部工单 done 后输出 ALL_DONE
