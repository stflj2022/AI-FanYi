# Ticket 011: M09 语音合成核心实现

## 状态: todo

## 优先级: 高

## 模块: M09 - Voice Synthesis

## 描述

实现 M09 语音合成的核心功能，支持多 TTS 模型、音色克隆和批量合成。

## 任务清单

- [ ] 创建 `src/filmdub/workers/voice_synthesis/` 目录结构
- [ ] 创建 `src/filmdub/workers/voice_synthesis/config.py` - 配置
- [ ] 创建 `src/filmdub/workers/voice_synthesis/model_manager.py` - 模型管理器
  - [ ] TTSModelManager 类
  - [ ] load_model() - 加载模型
  - [ ] switch_model() - 切换模型
  - [ ] unload_model() - 卸载模型
  - [ ] get_model_info() - 获取模型信息
  - [ ] 集成 CosyVoice
  - [ ] 集成 F5-TTS (可选)
- [ ] 创建 `src/filmdub/workers/voice_synthesis/tts_engine.py` - TTS 引擎
  - [ ] TTSEngine 类
  - [ ] synthesize() - 合成语音
  - [ ] _preprocess_text() - 前处理文本
  - [ ] _postprocess_audio() - 后处理音频
  - [ ] _apply_pitch_shift() - 音高偏移
  - [ ] _apply_time_stretch() - 时间拉伸
  - [ ] _save_audio() - 保存音频
- [ ] 创建 `src/filmdub/workers/voice_synthesis/batch_synthesizer.py` - 批量合成器
  - [ ] BatchSynthesizer 类
  - [ ] synthesize_batch() - 批量合成
  - [ ] _synthesize_with_semaphore() - 并发控制
- [ ] 创建 `src/filmdub/workers/voice_synthesis/models.py` - 数据模型
  - [ ] M09Input 数据类
  - [ ] M09Output 数据类
  - [ ] PreparedDialogue 数据类
  - [ ] AudioArtifact 数据类
- [ ] 创建 `src/filmdub/workers/voice_synthesis/main.py` - Worker 入口
- [ ] 实现音高变换 (pyrubberband)
- [ ] 实现时间拉伸
- [ ] 编写单元测试
- [ ] 编写语音合成测试

## 依赖

- Ticket 001: 数据库模型
- Ticket 002: Artifact Registry
- Ticket 010: M08 韵律规划

## 输出

- M09 语音合成实现
- 模型管理器
- TTS 引擎
- 批量合成器
- 测试文件

## 验收标准

1. 可以成功合成语音
2. 支持多种情绪
3. 语速和音高调整正确
4. 批量合成稳定
5. 测试通过

## 参考 ADR

- ADR 0011: M09 语音合成模块设计
- specs/m09-voice-synthesis.md
