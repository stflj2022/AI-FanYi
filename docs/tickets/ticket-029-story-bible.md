# Ticket 029: Story Bible（剧情数据库）

## 状态: todo

## 优先级: P0

## 模块: M06 翻译 / 长期资产

## 描述

实现 Story Bible（剧情数据库）——计划书反复强调的核心长期资产。建立剧情条目（角色/事件/关系/时间线/剧情状态），用于保证翻译的剧情一致性、人物语气统一，并作为 M06 翻译的上下文。

参考：计划书 1 1.20、2.7 节。

## 任务清单

- [ ] 在 `src/filmdub/core/models/` 增加 StoryEntry 模型（项目/角色/事件/关系/时间线/状态字段）
- [ ] Alembic 迁移
- [ ] 实现 Story Bible 存储与查询服务
- [ ] 创建 `src/filmdub/workers/story_bible/` worker：从剧本/字幕/人物库自动提取剧情条目
- [ ] 接入 M06 翻译：Qwen 翻译 prompt 携带剧情上下文（角色语气、剧情状态）
- [ ] 编写单元测试（test_story_bible.py, test_translation_story_context.py）

## 验收标准

- Story Bible 模型 + 迁移 + 服务完成
- 翻译能读取剧情上下文
- 测试通过
