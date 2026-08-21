# Ticket 008: M05 音频分析核心实现

## 状态: todo

## 优先级: 高

## 模块: M05 - Audio & Scene Analysis

## 描述

实现 M05 的核心音频分析功能，包括说话人识别、嵌入提取和音频特征提取。

## 任务清单

- [ ] 创建 `src/filmdub/workers/audio_scene_analysis/` 目录结构
- [ ] 创建 `src/filmdub/workers/audio_scene_analysis/config.py` - 配置
- [ ] 创建 `src/filmdub/workers/audio_scene_analysis/diarization.py` - 说话人识别
  - [ ] SpeakerDiarization 类
  - [ ] diarize() - 说话人分离
  - [ ] 集成 pyannote.audio
- [ ] 创建 `src/filmdub/workers/audio_scene_analysis/embedding.py` - 嵌入提取
  - [ ] SpeakerEmbeddingExtractor 类
  - [ ] extract() - 提取嵌入
  - [ ] _group_by_speaker() - 按说话人分组
  - [ ] _concatenate_segments() - 拼接片段
  - [ ] 集成 speechbrain ECAPA-TDNN
- [ ] 创建 `src/filmdub/workers/audio_scene_analysis/audio_features.py` - 音频特征
  - [ ] AudioFeatureExtractor 类
  - [ ] extract() - 提取特征
  - [ ] _extract_pitch() - 提取音高
  - [ ] _extract_energy() - 提取能量
  - [ ] _extract_spectral() - 提取频谱
  - [ ] _extract_mfcc() - 提取 MFCC
  - [ ] 集成 librosa
- [ ] 创建 `src/filmdub/workers/audio_scene_analysis/models.py` - 数据模型
  - [ ] SpeakerEmbedding 数据类
  - [ ] AudioFeatures 数据类
  - [ ] SpeakerSegment 数据类
- [ ] 创建 `src/filmdub/workers/audio_scene_analysis/main.py` - Worker 入口
- [ ] 编写单元测试
- [ ] 编写音频处理测试

## 依赖

- Ticket 001: 数据库模型
- Ticket 002: Artifact Registry

## 输出

- M05 核心音频分析实现
- 说话人识别
- 嵌入提取
- 音频特征提取
- 测试文件

## 验收标准

1. 说话人识别准确
2. 嵌入提取正确
3. 音频特征准确
4. 测试通过

## 参考 ADR

- ADR 0016: M05 音频与场景分析
- specs/m05-audio-scene-analysis.md
