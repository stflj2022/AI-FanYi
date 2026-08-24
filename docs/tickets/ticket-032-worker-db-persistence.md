# Ticket 032: worker→DB 持久化打通

## 状态: todo

## 优先级: P1

## 模块: Layer 0 / M03 M04 M05

## 描述

打通 worker 产出与 orchestrator 数据库：M03（人物库）、M04（声音库）、M05（音频分析）等 worker 的产出应写入 orchestrator 的 characters / voice_profiles / audio_analysis 等表，实现长期资产跨集跨季复用。

## 任务清单

- [ ] 梳理现有 worker 产出（research_* 表 vs orchestrator 表双轨问题）
- [ ] character_db worker 写入 characters 表（含 speech_pattern 填充）
- [ ] voice_synthesis / speaker_mapping 产出写入 voice_profiles 表（音色/参数版本/参考音频）
- [ ] audio_scene_analysis 产出写入 audio_analysis 表
- [ ] 提供跨集复用查询接口（get_character_by_name, get_voice_profile_by_character）
- [ ] 编写单元测试（test_worker_db_persistence.py）

## 验收标准

- worker 运行后 characters/voice_profiles/audio_analysis 表有数据
- 跨集能查询复用已有资产
- 测试通过
