# ADR 0011: M09 语音合成模块设计

## 状态

设计中

## 上下文

M09 语音合成是整个平台的核心计算模块之一，负责将中文对白转换为 AI 语音，是整个配音生产的关键环节。

## 核心职责

1. **TTS 模型管理**: 管理多个 TTS 模型（CosyVoice、F5-TTS 等）
2. **音色克隆**: 根据原演员声音创建 Voice Profile
3. **语音合成**: 将中文台词转换为语音
4. **情绪控制**: 根据对白情绪调整语音
5. **语速控制**: 匹配视频时长的语速调整
6. **批量处理**: 高效批量合成

## 输入/输出

### 输入

```python
@dataclass
class M09Input:
    """M09 输入数据结构"""
    project_id: uuid.UUID
    job_id: uuid.UUID

    # 对白数据（来自 M08）
    dialogues: List[PreparedDialogue]

    # Voice Profile 映射（来自 M06/M04）
    voice_profiles: Dict[str, uuid.UUID]  # character_id -> voice_profile_id

    # 全局配置
    config: SynthesisConfig

@dataclass
class PreparedDialogue:
    """准备好的对白"""
    id: str
    character_id: uuid.UUID
    text: str

    # 韵律参数（来自 M08）
    prosody: ProsodyParams

    # 时间约束
    target_duration: Optional[float] = None  # 目标时长（秒）
    max_duration: Optional[float] = None      # 最大时长

@dataclass
class ProsodyParams:
    """韵律参数"""
    emotion: Emotion = Emotion.NEUTRAL
    emotion_intensity: float = 0.5      # 0.0-1.0

    speed: float = 1.0                  # 语速倍数
    pitch: float = 0.0                  # 音高偏移（半音）

    # 停顿
    pause_before_ms: int = 0
    pause_after_ms: int = 0

    # 强调
    emphasis_words: List[str] = None

    # 呼吸
    add_breath: bool = False

class Emotion(Enum):
    """情绪类型"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    SURPRISED = "surprised"
    CALM = "calm"
    EXCITED = "excited"

@dataclass
class SynthesisConfig:
    """合成配置"""
    # 模型选择
    tts_model: str = "cosyvoice"
    model_version: str = "latest"

    # 质量设置
    sample_rate: int = 22050
    bit_depth: int = 16

    # 性能设置
    batch_size: int = 32
    use_gpu: bool = True
    gpu_memory_fraction: float = 0.8

    # 输出格式
    output_format: str = "wav"
    output_codec: str = "pcm_s16le"

    # 并发
    max_concurrent_jobs: int = 4
```

### 输出

```python
@dataclass
class M09Output:
    """M09 输出数据结构"""
    # 合成的音频
    audio_artifacts: List[AudioArtifact]

    # 统计信息
    statistics: SynthesisStatistics

@dataclass
class AudioArtifact:
    """音频 Artifact"""
    dialogue_id: str
    character_id: uuid.UUID
    artifact_id: uuid.UUID

    # 音频信息
    duration: float
    sample_rate: int
    channels: int

    # 元数据
    metadata: AudioMetadata

@dataclass
class AudioMetadata:
    """音频元数据"""
    text: str
    model: str
    voice_profile_id: uuid.UUID

    # 韵律参数
    prosody: ProsodyParams

    # 质量指标
    snr_db: Optional[float] = None        # 信噪比
    perplexity: Optional[float] = None    # 困惑度

@dataclass
class SynthesisStatistics:
    """合成统计"""
    total_dialogues: int
    successful: int
    failed: int
    total_duration: float
    average_synthesis_time: float
    real_time_factor: float             # 合成时间 / 音频时长
```

## 模块架构

```
┌───────────────────────────────────────────────────────────┐
│                         M09                                │
├───────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │   模型管理器      │      │   音色克隆器      │           │
│  │  (模型加载/切换)   │      │  (Voice Profile) │           │
│  └──────────────────┘      └──────────────────┘           │
│         │                          │                          │
│         └──────────┬───────────────┘                          │
│                    ▼                                          │
│         ┌────────────────────────┐                            │
│         │      任务调度器          │                            │
│         │   (批量/优先级/并发)      │                            │
│         └────────────────────────┘                            │
│                    │                                          │
│         ┌──────────┴──────────┐                               │
│         ▼                     ▼                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │   前处理器     │      │   后处理器     │                     │
│  │  (文本处理)    │      │  (音频处理)    │                     │
│  └──────────────┘      └──────────────┘                     │
│         │                     │                                 │
│         └──────────┬──────────┘                               │
│                    ▼                                         │
│         ┌────────────────────────┐                            │
│         │      TTS 引擎           │                            │
│         │  (CosyVoice/F5-TTS)    │                            │
│         └────────────────────────┘                            │
│                    │                                         │
│                    ▼                                         │
│         ┌────────────────────────┐                            │
│         │    质量验证器            │                            │
│         │  (SNR/时长/一致性)        │                            │
│         └────────────────────────┘                            │
└───────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. 模型管理器

```python
class TTSModelManager:
    """TTS 模型管理器"""

    def __init__(self, config_path: str = None):
        self.models = {}
        self.current_model = None
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> Dict:
        """加载模型配置"""
        default_config = {
            "cosyvoice": {
                "model_path": "models/CosyVoice-2.0",
                "config_path": "models/CosyVoice-2.0/config.json",
                "speaker_encoder_path": "models/CosyVoice-2.0/speaker_encoder.pt",
                "default_sample_rate": 22050
            },
            "f5-tts": {
                "model_path": "models/F5-TTS",
                "config_path": "models/F5-TTS/config.yaml",
                "default_sample_rate": 24000
            },
            "xtts": {
                "model_path": "models/XTTS",
                "config_path": "models/XTTS/config.json",
                "default_sample_rate": 24000
            }
        }

        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    async def load_model(self, model_name: str, use_gpu: bool = True) -> None:
        """加载 TTS 模型"""
        if model_name in self.models:
            self.current_model = self.models[model_name]
            return

        if model_name not in self.config:
            raise ValueError(f"Unknown model: {model_name}")

        model_config = self.config[model_name]

        # 根据模型类型加载
        if model_name == "cosyvoice":
            model = await self._load_cosyvoice(model_config, use_gpu)
        elif model_name == "f5-tts":
            model = await self._load_f5_tts(model_config, use_gpu)
        elif model_name == "xtts":
            model = await self._load_xtts(model_config, use_gpu)
        else:
            raise ValueError(f"Unsupported model: {model_name}")

        self.models[model_name] = model
        self.current_model = model

        logger.info(f"Loaded TTS model: {model_name}")

    async def _load_cosyvoice(
        self,
        config: Dict,
        use_gpu: bool
    ) -> CosyVoiceModel:
        """加载 CosyVoice 模型"""
        from cosyvoice.utils.file_utils import load_model

        model = await load_model(
            config["model_path"],
            device="cuda" if use_gpu else "cpu"
        )

        return CosyVoiceModel(
            model=model,
            sample_rate=config["default_sample_rate"],
            config=config
        )

    async def _load_f5_tts(
        self,
        config: Dict,
        use_gpu: bool
    ) -> F5TTSModel:
        """加载 F5-TTS 模型"""
        # 类似的加载逻辑
        pass

    async def switch_model(self, model_name: str) -> None:
        """切换当前模型"""
        if model_name not in self.models:
            await self.load_model(model_name)

        self.current_model = self.models[model_name]
        logger.info(f"Switched to model: {model_name}")

    async def unload_model(self, model_name: str) -> None:
        """卸载模型（释放内存）"""
        if model_name in self.models:
            del self.models[model_name]

            if self.current_model and \
               self.current_model.name == model_name:
                self.current_model = None

            logger.info(f"Unloaded model: {model_name}")

    async def get_model_info(self, model_name: str) -> Dict:
        """获取模型信息"""
        if model_name not in self.config:
            raise ValueError(f"Unknown model: {model_name}")

        config = self.config[model_name]

        # 检查模型是否已加载
        is_loaded = model_name in self.models

        # 获取模型大小
        model_size = 0
        if os.path.exists(config["model_path"]):
            model_size = sum(
                os.path.getsize(os.path.join(root, file))
                for root, _, files in os.walk(config["model_path"])
                for file in files
            )

        return {
            "name": model_name,
            "is_loaded": is_loaded,
            "model_path": config["model_path"],
            "sample_rate": config["default_sample_rate"],
            "size_bytes": model_size
        }
```

### 2. 音色克隆器

```python
class VoiceCloner:
    """音色克隆器"""

    def __init__(self, model_manager: TTSModelManager):
        self.model_manager = model_manager

    async def clone_voice(
        self,
        reference_audio: bytes,
        character_id: uuid.UUID,
        voice_profile_id: uuid.UUID
    ) -> VoiceProfile:
        """从参考音频克隆音色"""
        # 提取音色特征
        speaker_embedding = await self._extract_speaker_embedding(
            reference_audio
        )

        # 创建 Voice Profile
        voice_profile = VoiceProfile(
            id=voice_profile_id,
            character_id=character_id,
            speaker_embedding=speaker_embedding,
            model=self.model_manager.current_model.name,
            reference_audio_artifact_id=await self._save_reference_audio(
                reference_audio, voice_profile_id
            )
        )

        return voice_profile

    async def _extract_speaker_embedding(
        self,
        audio: bytes
    ) -> np.ndarray:
        """提取说话人嵌入"""
        # 保存临时文件
        temp_path = f"/tmp/{uuid.uuid4()}.wav"
        with open(temp_path, 'wb') as f:
            f.write(audio)

        try:
            # 使用模型的 speaker encoder
            model = self.model_manager.current_model

            if hasattr(model, 'extract_speaker_embedding'):
                embedding = await model.extract_speaker_embedding(temp_path)
            else:
                # 使用独立的说话人编码器
                embedding = await self._use_external_encoder(temp_path)

            return embedding

        finally:
            os.remove(temp_path)

    async def _use_external_encoder(self, audio_path: str) -> np.ndarray:
        """使用外部说话人编码器"""
        from speechbrain.inference.speaker import SpeakerRecognition

        verification = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="pretrained_models"
        )

        embedding = verification.verify_embeddings(
            audio_path,
            audio_path  # 使用相同音频作为示例
        )

        return embedding

    async def _save_reference_audio(
        self,
        audio: bytes,
        voice_profile_id: uuid.UUID
    ) -> uuid.UUID:
        """保存参考音频到 Artifact Registry"""
        # 创建 Artifact
        metadata = ArtifactMetadata(
            name=f"reference_{voice_profile_id}.wav",
            type=ArtifactType.AUDIO,
            project_id=None,  # 设置适当的 project_id
            job_id=None,
            module_id="M09",
            mime_type="audio/wav"
        )

        artifact_ref = await self.artifact_registry.create(metadata)

        # 上传音频
        await self.artifact_registry.upload(
            artifact_ref.id,
            io.BytesIO(audio)
        )

        return artifact_ref.id
```

### 3. TTS 引擎

```python
class TTSEngine:
    """TTS 引擎"""

    def __init__(
        self,
        model_manager: TTSModelManager,
        artifact_registry: ArtifactRegistry
    ):
        self.model_manager = model_manager
        self.artifact_registry = artifact_registry

    async def synthesize(
        self,
        dialogue: PreparedDialogue,
        voice_profile: VoiceProfile,
        output_format: str = "wav"
    ) -> AudioArtifact:
        """合成单句对白"""
        start_time = time.time()

        # 前处理
        processed_text = await self._preprocess_text(
            dialogue.text,
            dialogue.prosody
        )

        # 调用 TTS 模型
        model = self.model_manager.current_model

        audio_data, sample_rate = await model.synthesize(
            text=processed_text,
            speaker_embedding=voice_profile.speaker_embedding,
            prosody=dialogue.prosody,
            target_duration=dialogue.target_duration
        )

        # 后处理
        audio_data = await self._postprocess_audio(
            audio_data,
            dialogue.prosody
        )

        # 保存为 Artifact
        artifact_id = await self._save_audio(
            audio_data,
            sample_rate,
            dialogue.id,
            dialogue.character_id,
            output_format
        )

        # 计算时长
        duration = len(audio_data) / sample_rate

        synthesis_time = time.time() - start_time

        return AudioArtifact(
            dialogue_id=dialogue.id,
            character_id=dialogue.character_id,
            artifact_id=artifact_id,
            duration=duration,
            sample_rate=sample_rate,
            channels=1,
            metadata=AudioMetadata(
                text=dialogue.text,
                model=model.name,
                voice_profile_id=voice_profile.id,
                prosody=dialogue.prosody,
                synthesis_time=synthesis_time
            )
        )

    async def _preprocess_text(
        self,
        text: str,
        prosody: ProsodyParams
    ) -> str:
        """前处理文本"""
        # 添加停顿标记
        if prosody.pause_before_ms > 0:
            text = f"[{prosody.pause_before_ms}ms]" + text

        if prosody.pause_after_ms > 0:
            text = text + f"[{prosody.pause_after_ms}ms]"

        # 添加呼吸标记
        if prosody.add_breath:
            text = "[breath]" + text

        # 处理强调词汇
        if prosody.emphasis_words:
            for word in prosody.emphasis_words:
                text = text.replace(
                    word,
                    f"<emphasis>{word}</emphasis>"
                )

        return text

    async def _postprocess_audio(
        self,
        audio_data: np.ndarray,
        prosody: ProsodyParams
    ) -> np.ndarray:
        """后处理音频"""
        # 应用音高偏移
        if prosody.pitch != 0:
            audio_data = self._apply_pitch_shift(
                audio_data,
                prosody.pitch
            )

        # 应用速度调整
        if prosody.speed != 1.0:
            audio_data = self._apply_time_stretch(
                audio_data,
                1.0 / prosody.speed
            )

        # 添加呼吸声
        if prosody.add_breath:
            audio_data = self._add_breath_sound(audio_data)

        return audio_data

    def _apply_pitch_shift(
        self,
        audio: np.ndarray,
        semitones: float
    ) -> np.ndarray:
        """应用音高偏移"""
        import pyrubberband as pyrb

        # 使用 Rubber Band 库进行音高变换
        shifted = pyrb.pitch_shift(
            audio,
            sr=22050,  # 假设采样率
            n_steps=semitones
        )

        return shifted

    def _apply_time_stretch(
        self,
        audio: np.ndarray,
        rate: float
    ) -> np.ndarray:
        """应用时间拉伸"""
        import pyrubberband as pyrb

        stretched = pyrb.time_stretch(
            audio,
            sr=22050,
            rate=rate
        )

        return stretched

    def _add_breath_sound(self, audio: np.ndarray) -> np.ndarray:
        """添加呼吸声"""
        # 简化处理：在音频开始处添加噪声
        breath_samples = int(0.1 * 22050)  # 0.1秒
        breath = np.random.normal(0, 0.01, breath_samples)

        # 淡入淡出
        breath[:breath_samples//4] *= np.linspace(0, 1, breath_samples//4)
        breath[-breath_samples//4:] *= np.linspace(1, 0, breath_samples//4)

        return np.concatenate([breath, audio])

    async def _save_audio(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        dialogue_id: str,
        character_id: uuid.UUID,
        output_format: str
    ) -> uuid.UUID:
        """保存音频为 Artifact"""
        # 创建 Artifact
        metadata = ArtifactMetadata(
            name=f"{dialogue_id}.{output_format}",
            type=ArtifactType.AUDIO,
            project_id=None,
            job_id=None,
            module_id="M09",
            mime_type=f"audio/{output_format}"
        )

        artifact_ref = await self.artifact_registry.create(metadata)

        # 转换为字节
        import io
        buffer = io.BytesIO()

        if output_format == "wav":
            import wave
            with wave.open(buffer, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes((audio_data * 32767).astype(np.int16))

        buffer.seek(0)

        # 上传
        await self.artifact_registry.upload(
            artifact_ref.id,
            buffer
        )

        return artifact_ref.id
```

### 4. 批量合成器

```python
class BatchSynthesizer:
    """批量合成器"""

    def __init__(
        self,
        tts_engine: TTSEngine,
        max_concurrent: int = 4
    ):
        self.tts_engine = tts_engine
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def synthesize_batch(
        self,
        dialogues: List[PreparedDialogue],
        voice_profiles: Dict[uuid.UUID, VoiceProfile],
        progress_callback: Optional[Callable] = None
    ) -> List[AudioArtifact]:
        """批量合成"""
        tasks = []

        for dialogue in dialogues:
            voice_profile = voice_profiles.get(
                dialogue.character_id
            )

            if not voice_profile:
                logger.warning(
                    f"No voice profile for character {dialogue.character_id}"
                )
                continue

            task = self._synthesize_with_semaphore(
                dialogue,
                voice_profile,
                progress_callback
            )

            tasks.append(task)

        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        audio_artifacts = []
        failed = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Synthesis failed for dialogue {dialogues[i].id}: {result}")
                failed.append((dialogues[i].id, str(result)))
            else:
                audio_artifacts.append(result)

        if progress_callback:
            await progress_callback(100, len(audio_artifacts), len(failed))

        return audio_artifacts

    async def _synthesize_with_semaphore(
        self,
        dialogue: PreparedDialogue,
        voice_profile: VoiceProfile,
        progress_callback: Optional[Callable]
    ) -> AudioArtifact:
        """使用信号量控制的合成"""
        async with self.semaphore:
            result = await self.tts_engine.synthesize(dialogue, voice_profile)

            if progress_callback:
                await progress_callback(None, 1, 0)

            return result
```

### 5. 质量验证器

```python
class QualityValidator:
    """质量验证器"""

    async def validate_audio(
        self,
        audio_artifact: AudioArtifact
    ) -> ValidationResult:
        """验证音频质量"""
        issues = []
        warnings = []

        # 检查时长
        if audio_artifact.duration < 0.1:
            issues.append("Audio duration too short")

        if audio_artifact.duration > 60:
            warnings.append("Audio duration very long")

        # 检查采样率
        if audio_artifact.sample_rate < 16000:
            issues.append("Sample rate too low")

        # 检查音量
        audio_data = await self._load_audio(audio_artifact)
        rms = np.sqrt(np.mean(audio_data**2))

        if rms < 0.01:
            issues.append("Audio level too low")
        elif rms > 0.9:
            warnings.append("Audio level may clip")

        # 检查 SNR
        snr = self._calculate_snr(audio_data)
        if snr < 20:
            warnings.append(f"Low SNR: {snr:.1f} dB")

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            warnings=warnings
        )

    async def _load_audio(
        self,
        audio_artifact: AudioArtifact
    ) -> np.ndarray:
        """加载音频数据"""
        # 从 Artifact Registry 下载
        audio_bytes = await self.artifact_registry.download(
            audio_artifact.artifact_id
        )

        # 解码
        import io
        import wave

        buffer = io.BytesIO(audio_bytes)
        with wave.open(buffer, 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            audio_data = np.frombuffer(frames, dtype=np.int16)
            audio_data = audio_data.astype(np.float32) / 32768.0

        return audio_data

    def _calculate_snr(self, audio: np.ndarray) -> float:
        """计算信噪比"""
        # 简化的 SNR 计算
        signal_power = np.mean(audio**2)

        # 使用静音段估计噪声功率
        # 简化处理：使用最低 10% 的功率作为噪声估计
        sorted_powers = np.sort(audio**2)
        noise_power = np.mean(sorted_powers[:len(sorted_powers)//10])

        if noise_power == 0:
            return float('inf')

        snr = 10 * np.log10(signal_power / noise_power)
        return snr
```

## 错误处理

### 错误代码

| 代码 | 描述 | 可重试 |
|------|------|--------|
| M009-001 | TTS 模型加载失败 | 是 |
| M009-002 | 音色克隆失败 | 否 |
| M009-003 | 语音合成失败 | 是 |
| M009-004 | 音频处理失败 | 否 |
| M009-005 | GPU 内存不足 | 是 |
| M009-006 | 质量验证失败 | 否 |

### 降级策略

1. **主模型失败**: 切换到备用模型
2. **GPU 不足**: 切换到 CPU
3. **音色克隆失败**: 使用默认音色
4. **时长不匹配**: 调整语速重新合成

## 性能优化

1. **批量处理**: 批量合成提高吞吐量
2. **GPU 利用**: 多并发充分利用 GPU
3. **模型缓存**: 常用模型保持加载状态
4. **音频流式**: 流式处理减少内存占用

## 测试要点

1. 各种情绪的语音质量
2. 语速调整准确性
3. 音高偏移效果
4. 批量合成稳定性
5. 内存使用情况
6. GPU 内存管理

## 后续模块依赖

M09 的输出被以下模块使用：
- **M10**: 合成的音频用于混音
- **M11**: 合成的音频用于视频组装
