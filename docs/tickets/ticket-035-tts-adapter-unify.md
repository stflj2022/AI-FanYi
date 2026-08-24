# Ticket 035: TTS Adapter 统一

## 状态: todo

## 优先级: P2

## 模块: M09 TTS / Adapter

## 描述

统一 TTS Adapter：当前 CosyVoice/F5-TTS 走 model.inference 直接调用、Qwen 走 adapter/voice.py 双路径并存。按计划书 3.x"能力与实现分离"原则，将 CosyVoice/F5-TTS 统一并入 `adapter/voice.py` 的 VoiceAdapterInterface，实现可配置切换。

参考：计划书 1 3.1~3.4 节。

## 任务清单

- [ ] 梳理 adapter/voice.py 现有接口与 voice_synthesis/model_manager.py 的 CosyVoice/F5 路径
- [ ] 实现 CosyVoiceAdapter / F5TTSAdapter（实现 VoiceAdapterInterface.synthesize）
- [ ] 统一 model_manager 走 Adapter 接口（backend 配置切换：qwen/cosyvoice/f5-tts）
- [ ] TTS 模型版本/参数进入 Artifact（可复现）
- [ ] 编写单元测试（test_tts_adapter_unify.py）

## 验收标准

- 通过配置切换 TTS backend，无需改业务代码
- CosyVoice/F5 与 Qwen 统一走 Adapter
- 测试通过
