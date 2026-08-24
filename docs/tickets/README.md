# AI-FanYi 工单列表

本文档列出所有工单及其状态。

## 工单状态

- `todo`: 待处理
- `doing`: 进行中
- `done`: 已完成
- `blocked`: 已阻塞

## 工单列表

### Layer 0 Orchestrator

| ID | 工单名称 | 状态 | 优先级 | 依赖 |
|----|---------|------|--------|------|
| 001 | Layer 0 数据库模型和迁移 | done | 高 | - |
| 002 | Artifact Registry 实现 | done | 高 | 001 |
| 003 | REST API - 项目和作业管理 | done | 高 | 001, 002 |
| 004 | Worker 管理器实现 | done | 高 | 001, 003 |
| 005 | 调度器核心实现 | done | 高 | 001, 002, 004 |
| 015 | WebSocket 实时通信 | done | 中 | 003, 013 |

### M04 - Character Database

| ID | 工单名称 | 状态 | 优先级 | 依赖 |
|----|---------|------|--------|------|
| 006 | M04 人物数据库核心实现 | done | 高 | 001, 002 |
| 007 | M04 人物关系构建 | done | 中 | 006 |

### M05 - Audio & Scene Analysis

| ID | 工单名称 | 状态 | 优先级 | 依赖 |
|----|---------|------|--------|------|
| 008 | M05 音频分析核心实现 | done | 高 | 001, 002 |

### M06 - Speaker Mapping

| ID | 工单名称 | 状态 | 优先级 | 依赖 |
|----|---------|------|--------|------|
| 009 | M06 说话人到人物映射 | done | 高 | 001, 002, 006, 008 |

### M07 - Dialogue Intelligence & M08 - Prosody Planning

| ID | 工单名称 | 状态 | 优先级 | 依赖 |
|----|---------|------|--------|------|
| 010 | M07 对白智能处理 + M08 韵律规划 | done | 高 | 001, 002, 006, 008, 009 |

### M09 - Voice Synthesis

| ID | 工单名称 | 状态 | 优先级 | 依赖 |
|----|---------|------|--------|------|
| 011 | M09 语音合成核心实现 | done | 高 | 001, 002, 010 |

### M11 - Video Assembly

| ID | 工单名称 | 状态 | 优先级 | 依赖 |
|----|---------|------|--------|------|
| 012 | M11 视频组装与最终编码 | done | 高 | 001, 002, 011 |

### Web Frontend

| ID | 工单名称 | 状态 | 优先级 | 依赖 |
|----|---------|------|--------|------|
| 013 | Web 前端框架搭建 | done | 中 | 003 |
| 014 | Web 前端 - Dashboard 和 Projects 页面 | done | 中 | 013 |

### qwen-tts 集成（阶段 1）

| ID | 工单名称 | 状态 | 优先级 | 依赖 |
|----|---------|------|--------|------|
| 016 | Adapter 层集成到各模块 | done | 高 | - |
| 017 | qwen-tts Service 健康检查与自动重启 | done | 高 | 016, 015 |
| 018 | 短视频端到端测试 | done | 高 | 016, 017 |

### 阶段2：理解层模块

| ID | 工单名称 | 状态 | 优先级 | 依赖 |
|----|---------|------|--------|------|
| 019 | 翻译模块实现 | done | 高 | 003, 006 |
| 020 | 人脸识别与角色追踪 | done | 高 | 006, 002 |

### 阶段4：组装层模块

| ID | 工单名称 | 状态 | 优先级 | 依赖 |
|----|---------|------|--------|------|
| 021 | M12 视频封装 | done | 高 | 011, 002 |
| 022 | M13 QA 模块 | done | 高 | 021, 006 |
| 023 | M14 归档模块 | done | 高 | 022, 002, 006 |

## 实施顺序

### Phase 1 (立即开始)
1. Ticket 001: Layer 0 数据库模型和迁移
2. Ticket 002: Artifact Registry 实现
3. Ticket 003: REST API - 项目和作业管理
4. Ticket 006: M04 人物数据库核心实现
5. Ticket 008: M05 音频分析核心实现

### Phase 2 (核心功能)
6. Ticket 004: Worker 管理器实现
7. Ticket 005: 调度器核心实现
8. Ticket 009: M06 说话人到人物映射
9. Ticket 010: M07 对白智能处理 + M08 韵律规划

### Phase 3 (语音和视频)
10. Ticket 011: M09 语音合成核心实现
11. Ticket 012: M11 视频组装与最终编码
12. Ticket 007: M04 人物关系构建

### Phase 4 (前端和实时)
13. Ticket 013: Web 前端框架搭建
14. Ticket 014: Web 前端 - Dashboard 和 Projects 页面
15. Ticket 015: WebSocket 实时通信

### Phase 5 (组装层)
16. Ticket 021: M12 视频封装
17. Ticket 022: M13 QA 模块
18. Ticket 023: M14 归档模块

### Phase 6 (Web 完整流水线)
19. Ticket 036: Web 配音任务接入完整 M01~M14 流水线
20. Ticket 037: 任务进度/阶段实时展示
21. Ticket 038: 成品输出 - 最终视频在线播放/下载 + QA 报告
22. Ticket 039: 人物数据库 + 翻译记忆 UI 入口
23. Ticket 040: Layer 0 动态调度完善
24. Ticket 041: laobai 端到端验证

## 统计

- 总工单数: 41
- 待处理: 3
- 进行中: 0
- 已完成: 38
- 已阻塞: 0

## Ticket 018: 短视频端到端测试完成

**完成时间**: 2026-08-23

**解决问题**:
- qwen-tts 服务端口冲突（8080 被 llama-server 占用）
- 修改 VoiceAdapter 默认端口从 8080 改为 8081
- 启动 tts-server（127.0.0.1:8081）
- 安装 pytest-mock 修复测试依赖

**测试结果**:
- TestEndToEndLaobai::test_full_pipeline_laobai: PASSED
- TestEndToEndPingi::test_full_pipeline_pingi: PASSED
- TestEndToEndPerformance::test_performance_metrics: PASSED
- **全量测试**: 407 passed, 5 skipped, 534 warnings

**性能指标**:
- laobai.mp4: 分离 34.6s, 转写 114.1s, 克隆 0.01s(使用默认音色), 合成 ~56s
- pingi.mp4: 类似性能

## 阶段2复验（第3轮）完成

全部 15 张工单复验通过：真实业务逻辑 + 测试 + 全量 pytest 绿后标记 done

## 阶段3：qwen-tts 集成（已完成）

- Ticket 016: Adapter 层实现（已完成）
- Ticket 016: Adapter 层集成到各模块（已完成）
- Ticket 017: qwen-tts Service 健康检查（已完成）
- Ticket 018: 短视频端到端测试（待处理）

## 备注

- 每完成 3 个工单，使用 code-review 技能检查一次
- 测试连续失败 3 次，标记工单为 blocked 并写明原因
- 每个 commit 后立即 git push
- 每轮结束确保 git 工作区干净
