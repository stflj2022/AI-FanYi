# Ticket 007: M04 人物关系构建

## 状态: todo

## 优先级: 中

## 模块: M04 - Character Database

## 描述

实现 M04 的人物关系构建功能，从对白中推断人物关系并构建关系图。

## 任务清单

- [ ] 创建 `src/filmdub/workers/character_db/relationships.py` - 关系构建器
  - [ ] RelationshipBuilder 类
  - [ ] build_relationships() - 构建关系
  - [ ] _find_interactions() - 查找交互
  - [ ] _mentions_character() - 检查提及
  - [ ] _infer_relationship() - 推断关系
  - [ ] _build_relationship_prompt() - 构建 LLM 提示
- [ ] 集成本地 LLM (Qwen)
- [ ] 实现关系类型定义
- [ ] 实现关系图构建
- [ ] 编写单元测试
- [ ] 编写关系推断测试

## 依赖

- Ticket 006: M04 核心实现

## 输出

- 关系构建器实现
- 关系图构建逻辑
- 测试文件

## 验收标准

1. 可以正确检测角色交互
2. LLM 关系推断合理
3. 关系图正确构建
4. 测试通过

## 参考 ADR

- ADR 0010: M04 人物数据库构建模块设计
