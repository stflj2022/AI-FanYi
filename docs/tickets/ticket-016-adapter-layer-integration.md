# Ticket 016: Adapter 层集成到各模块

## 状态: done

## 优先级: 高

## 模块: M02, M04, M05, M09

## 描述

将刚刚实现的 Adapter 层集成到各模块中，替代原有的直接调用方式：

- **M02 (Media Analysis)**: 使用 AudioSeparationAdapter 进行音频分离
- **M04 (Character DB)**: 使用 VoiceAdapter 进行音色克隆和管理
- **M05 (Audio Analysis)**: 使用 ASRAdapter 进行语音转写
- **M09 (Voice Synthesis)**: 使用 VoiceAdapter 进行语音合成

## 验收标准

- [ ] M02 使用 AudioSeparationAdapter 替代直接 HTDemucs 调用
- [ ] M04 使用 VoiceAdapter 管理克隆音色，存储在 `cloned_voices/` 目录
- [ ] M05 使用 ASRAdapter (Faster-Whisper) 进行转写
- [ ] M09 使用 VoiceAdapter 进行语音合成，调用 qwen-tts service
- [ ] 所有模块的现有测试通过（不破坏 M01-M03 已验证行为）
- [ ] 适配器层的测试全部通过（23 passed, 3 skipped）
- [ ] 短视频（laobai/pingi）跑通「分离→转写→克隆→合成」端到端

## 技术要点

1. **不破坏现有 API**: 各模块的公共接口保持不变，内部实现改用 adapter
2. **配置驱动**: adapter 后端选择通过配置文件/环境变量控制
3. **错误处理**: 优雅处理 adapter 不可用的情况
4. **性能考虑**: adapter 实例复用，避免重复初始化

## 依赖

- Ticket 016: Adapter 层实现（已完成）

## 预估工作量

2-3 天
