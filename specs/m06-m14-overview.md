# M06-M14 模块概览

本文档概述 M06-M14 模块的职责、输入输出和关键实现点。

---

## M06: Speaker → Character → Voice Identity Mapping

### 核心职责
- 将说话人 (Speaker) 映射到人物 (Character)
- 为人物分配 Voice Profile
- 处理跨集的一致性

### 输入 Artifact
- `speaker_embeddings` (来自 M05)
- `character_database` (来自 M04)
- `dialogue_timeline` (来自 M03)

### 输出 Artifact
- `dialogue_with_characters`: 包含人物信息的对白
- `voice_mapping`: 人物到音色的映射

### 关键实现
```python
class SpeakerToCharacterMapper:
    async def map_speakers(
        self,
        speaker_embeddings: List[SpeakerEmbedding],
        characters: List[Character]
    ) -> Dict[str, uuid.UUID]:
        """基于说话人嵌入和人物信息进行映射"""

    async def assign_voice_profiles(
        self,
        characters: List[Character]
    ) -> Dict[uuid.UUID, uuid.UUID]:
        """为人物分配 Voice Profile"""
```

### 优先级: 高

---

## M07: Subtitle / Dialogue Intelligence

### 核心职责
- 对白智能处理
- 上下文感知翻译优化
- 术语一致性检查
- 文化本地化调整

### 输入 Artifact
- `dialogue_with_characters` (来自 M06)
- `translation_memory` (来自 Story Bible)
- `character_database` (来自 M04)

### 输出 Artifact
- `processed_dialogue`: 处理后的对白
- `translation_adjustments`: 翻译调整记录

### 关键实现
```python
class DialogueIntelligence:
    async def process_dialogue(
        self,
        dialogue: Dialogue,
        context: Context
    ) -> ProcessedDialogue:
        """智能处理对白"""
        # 术语一致性
        # 文化本地化
        # 人物语气一致性
```

### 优先级: 高

---

## M08: Prosody & Performance Planning

### 核心职责
- 韵律参数规划
- 表演风格设定
- 语速和停顿规划
- 情绪强度调整

### 输入 Artifact
- `processed_dialogue` (来自 M07)
- `character_database` (来自 M04)
- `emotion_tags` (来自 M05)

### 输出 Artifact
- `dialogue_with_prosody`: 包含韵律参数的对白

### 关键实现
```python
class ProsodyPlanner:
    async def plan_prosody(
        self,
        dialogue: ProcessedDialogue,
        character: Character,
        emotion: Emotion
    ) -> ProsodyParams:
        """规划韵律参数"""
        # 语速
        # 音高
        # 停顿
        # 情绪强度
```

### 优先级: 高

---

## M09: Voice Synthesis

### 核心职责
- AI 语音合成
- 多模型支持 (CosyVoice, F5-TTS, XTTS)
- 音色克隆
- 情绪控制

### 输入 Artifact
- `dialogue_with_prosody` (来自 M08)
- `voice_profiles` (来自 M06)

### 输出 Artifact
- `generated_audio`: 合成的音频文件

### 优先级: 高

详见: `specs/m09-voice-synthesis.md`

---

## M10: Dialogue Audio Processing & Scene Mixing

### 核心职责
- 对白音频后处理
- 音量标准化
- 场景混音
- 环境音融合

### 输入 Artifact
- `generated_audio` (来自 M09)
- `scene_timeline` (来自 M05)
- `original_audio` (来自 M01)

### 输出 Artifact
- `mixed_audio_tracks`: 混音后的音频轨道

### 关键实现
```python
class AudioProcessor:
    async def process_audio(
        self,
        audio: AudioArtifact,
        config: ProcessingConfig
    ) -> ProcessedAudio:
        """音频后处理"""
        # 去噪
        # 均衡化
        # 压缩
```

### 优先级: 中

---

## M11: Video Assembly & Final Encoding

### 核心职责
- 视频组装
- 音视频同步
- 字幕嵌入
- 最终编码

### 输入 Artifact
- `mixed_audio_tracks` (来自 M10)
- `source_video` (来自 M01)
- `subtitle_timeline` (来自 M03)

### 输出 Artifact
- `final_video`: 最终配音视频

### 关键实现
```python
class VideoAssembler:
    async def assemble_video(
        self,
        video_path: str,
        audio_path: str,
        subtitle_path: Optional[str]
    ) -> str:
        """组装最终视频"""
```

### 优先级: 高

---

## M12: Project QA & Human Review

### 核心职责
- 自动质量检查
- 人工审查工作流
- 质量报告生成
- 问题跟踪

### 输入 Artifact
- `final_video` (来自 M11)
- `all_previous_artifacts`

### 输出 Artifact
- `qa_report`: 质检报告
- `review_status`: 审查状态

### 优先级: 中

---

## M13: Batch / Season Pipeline

### 核心职责
- 批量处理
- 季集流水线
- 并发调度
- 进度跟踪

### 输入
- 批量项目配置
- 季集信息

### 输出
- 批量处理结果

### 优先级: 低

---

## M14: Project Archive & Reproducibility

### 核心职责
- 项目归档
- Artifact 清理
- 可复现性保证
- 元数据导出

### 输入
- 完成项目的所有 Artifact

### 输出
- 归档包
- 元数据导出

### 优先级: 低

---

## 实现优先级总结

### Phase 1 (立即开始)
- M04: Character Database
- M05: Audio & Scene Analysis
- M06: Speaker Mapping
- M07: Dialogue Intelligence
- M08: Prosody Planning
- M09: Voice Synthesis
- M11: Video Assembly

### Phase 2 (后续迭代)
- M10: Audio Processing
- M12: QA & Review

### Phase 3 (高级功能)
- M13: Batch Pipeline
- M14: Archive

---

## 依赖关系图

```
M01 (已完成) → M02 (已完成) → M03 (已完成)
                                     ↓
M05 ← M04 ←──────────────────────────┘
 ↓      ↓
M06 ←───┘
 ↓
M07
 ↓
M08
 ↓
M09
 ↓
M10 ← (并行)
 ↓      ↓
M11 ←───┘
 ↓
M12
```

M13 (批量处理) 和 M14 (归档) 是独立的高级模块。
