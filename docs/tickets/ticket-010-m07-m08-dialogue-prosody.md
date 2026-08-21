# Ticket 010: M07 对白智能处理 + M08 韵律规划

## 状态: todo（第3轮：先修测试套件再真实实现，驱动独立pytest验收）

## 优先级: 高

## 模块: M07 - Dialogue Intelligence, M08 - Prosody Planning

## 描述

实现 M07 的对白智能处理和 M08 的韵律规划功能。

## 任务清单

### M07 部分
- [ ] 创建 `src/filmdub/workers/dialogue_intelligence/` 目录结构
- [ ] 创建 `src/filmdub/workers/dialogue_intelligence/processor.py` - 对白处理器
  - [ ] DialogueIntelligence 类
  - [ ] process_dialogue() - 处理对白
  - [ ] _check_terminology() - 检查术语一致性
  - [ ] _localize_culture() - 文化本地化
  - [ ] _adjust_tone() - 调整语气
- [ ] 集成本地 LLM (Qwen)
- [ ] 创建 `src/filmdub/workers/dialogue_intelligence/main.py` - Worker 入口

### M08 部分
- [ ] 创建 `src/filmdub/workers/prosody_planning/` 目录结构
- [ ] 创建 `src/filmdub/workers/prosody_planning/planner.py` - 韵律规划器
  - [ ] ProsodyPlanner 类
  - [ ] plan_prosody() - 规划韵律
  - [ ] _calculate_speed() - 计算语速
  - [ ] _calculate_pitch() - 计算音高
  - [ ] _calculate_pauses() - 计算停顿
  - [ ] _adjust_emotion() - 调整情绪
- [ ] 创建 `src/filmdub/workers/prosody_planning/models.py` - 数据模型
  - [ ] ProsodyParams 数据类
  - [ ] PreparedDialogue 数据类
- [ ] 创建 `src/filmdub/workers/prosody_planning/main.py` - Worker 入口
- [ ] 编写单元测试

## 依赖

- Ticket 001: 数据库模型
- Ticket 002: Artifact Registry
- Ticket 006: M04 人物数据库
- Ticket 008: M05 音频分析
- Ticket 009: M06 说话人映射

## 输出

- M07 对白处理器实现
- M08 韵律规划器实现
- 测试文件

## 验收标准

1. 对白智能处理合理
2. 韵律参数准确
3. 情绪表达正确
4. 测试通过

## 参考 ADR

- ADR 0018: M07 对白智能处理
- ADR 0019: M08 韵律规划
- specs/m06-m14-overview.md
