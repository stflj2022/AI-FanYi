# Ticket 036: Web 配音任务接入完整 M01~M14 流水线

## 状态: todo

## 优先级: P0

## 模块: 执行引擎 / Layer 0

## 描述

让 Web UI 创建的配音任务**自动走完整 M01~M14 流水线**，最终产出配音视频成品。

参考《计划书/ai-fanyi-web ui.txt》核心原则：Web UI 不直接调用 14 模块，只认识 Project/Job/Input/Output/Status；任务提交后交给 Layer 0 执行完整流水线。

`scripts/run_full_pipeline.py` 已实现完整 DAG（M01→M02→M03→M05→M04→M06→M07→M08→M09→M10→M11→M12→M13→M14），依赖外部服务 qwen-tts（8081 CLI）、ollama（11434, gemma4-e2b）、whisper——均已就绪。当前 Job Runner 只做 M01，需扩展到完整流水线。

## 任务清单

- [ ] 复用 `scripts/run_full_pipeline.py` 的 Orchestrator 能力（抽取 exec_M01~M14 或封装为可调用模块）
- [ ] Job Runner 处理配音任务：下载 Web 上传媒体（MinIO）→ 作为输入视频 → 执行完整流水线 → 产出 final 视频
- [ ] 各模块产出（对白、翻译、TTS、混音、最终视频）写入项目 artifacts 并注册
- [ ] 整条流水线完成后 Web 任务置 completed；任一模失败置 failed（error_message 定位失败模块）
- [ ] 支持断点续跑（已完成模块跳过，从失败模块继续）

## 验收标准

- Web UI 创建配音任务 → Job Runner 自动执行完整 M01~M14 → 产出 final_dubbed.mp4（真实中文语音）
- 任务状态自动流转 等待中→运行中→已完成
- 各模块 artifact 存在（对白/翻译/TTS/混音/最终视频）
