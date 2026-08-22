# Ticket 019: 翻译模块实现

## 状态: todo

## 优先级: 高

## 模块: M06-Translation

## 描述

实现翻译模块，将原始对白翻译成中文，支持术语一致性和文化本地化。

## 任务清单

- [ ] 创建 `src/filmdub/workers/translation/` 目录
- [ ] 实现翻译引擎基类 `TranslationEngine`
  - [ ] `translate()` - 翻译接口
  - [ ] `batch_translate()` - 批量翻译
  - [ ] `translate_with_context()` - 上下文感知翻译
- [ ] 实现 Qwen 翻译引擎 `QwenTranslationEngine`
  - [ ] 连接本地 Qwen 模型
  - [ ] 实现提示词模板
  - [ ] 处理术语一致性
  - [ ] 文化本地化调整
- [ ] 实现翻译记忆库 `TranslationMemory`
  - [ ] 存储翻译历史
  - [ ] 术语库管理
  - [ ] 查找相似翻译
- [ ] 实现翻译 Worker `M06Worker`
  - [ ] 读取对白时间轴
  - [ ] 调用翻译引擎
  - [ ] 应用翻译记忆
  - [ ] 保存翻译结果
- [ ] 集成到工作流
- [ ] 编写单元测试
- [ ] 编写集成测试

## 依赖

- Ticket 003: REST API - 项目和作业管理
- Ticket 006: M04 人物数据库核心实现

## 输出

- 翻译引擎实现
- 翻译记忆库
- 翻译 Worker
- 测试文件

## 验收标准

1. 可以成功翻译对白文本
2. 翻译结果符合中文表达习惯
3. 术语翻译一致
4. 人物语气保持一致
5. 单元测试通过
6. 集成测试通过

## 参考 ADR

- ADR 0007: 翻译模块设计
