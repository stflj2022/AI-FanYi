# Ticket 009: M06 说话人到人物映射

## 状态: todo

## 优先级: 高

## 模块: M06 - Speaker Mapping

## 描述

实现 M06 的核心功能，将说话人映射到人物，并分配 Voice Profile。

## 任务清单

- [ ] 创建 `src/filmdub/workers/speaker_mapping/` 目录结构
- [ ] 创建 `src/filmdub/workers/speaker_mapping/config.py` - 配置
- [ ] 创建 `src/filmdub/workers/speaker_mapping/mapper.py` - 映射器
  - [ ] SpeakerToCharacterMapper 类
  - [ ] map_speakers() - 映射说话人到人物
  - [ ] _calculate_similarity() - 计算相似度
  - [ ] _find_best_match() - 找到最佳匹配
  - [ ] _handle_new_speakers() - 处理新说话人
- [ ] 创建 `src/filmdub/workers/speaker_mapping/voice_assigner.py` - 音色分配器
  - [ ] VoiceProfileAssigner 类
  - [ ] assign_voice_profiles() - 分配音色
  - [ ] _create_voice_profile() - 创建音色
  - [ ] _reuse_voice_profile() - 复用音色
- [ ] 创建 `src/filmdub/workers/speaker_mapping/models.py` - 数据模型
- [ ] 创建 `src/filmdub/workers/speaker_mapping/main.py` - Worker 入口
- [ ] 实现相似度计算算法
- [ ] 编写单元测试

## 依赖

- Ticket 001: 数据库模型
- Ticket 002: Artifact Registry
- Ticket 006: M04 人物数据库
- Ticket 008: M05 音频分析

## 输出

- M06 映射器实现
- 音色分配器实现
- 测试文件

## 验收标准

1. 说话人正确映射到人物
2. 音色分配合理
3. 跨集一致性正确
4. 测试通过

## 参考 ADR

- ADR 0017: M06 说话人映射
- specs/m06-m14-overview.md
