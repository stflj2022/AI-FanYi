# ADR 0016: M05 音频与场景分析模块设计

## 状态

设计中

## 上下文

M05 负责音频分析、说话人识别、说话人嵌入提取，为 M06 的人物映射和 M04 的人物聚类提供关键数据。

## 核心职责

1. **音频特征提取**: 提取 MFCC、梅尔频谱等音频特征
2. **说话人识别**: 使用 Pyannote.audio 进行说话人分段
3. **说话人嵌入**: 为每个说话人生成嵌入向量
4. **音频分类**: 识别对白、音乐、音效
5. **场景音频分析**: 分析场景的声音环境

## 输入/输出

### 输入

```python
@dataclass
class M05Input:
    """M05 输入数据结构"""
    project_id: uuid.UUID
    job_id: uuid.UUID

    # 来自 M02 的视频 Artifact
    video_artifact_id: uuid.UUID

    # 来自 M02 的音频分析
    audio_analysis: AudioAnalysis

    # 配置
    config: AudioAnalysisConfig

@dataclass
class AudioAnalysisConfig:
    """音频分析配置"""
    # 说话人识别
    min_speakers: int = 2
    max_speakers: int = 10
    speaker_segmentation: bool = True

    # 音频特征
    extract_mfcc: bool = True
    extract_mel_spectrogram: bool = True
    extract_prosody: bool = True

    # 处理选项
    use_gpu: bool = True
    batch_size: int = 32
```

### 输出

```python
@dataclass
class M05Output:
    """M05 输出数据结构"""
    # 说话人嵌入
    speaker_embeddings: List[SpeakerEmbedding]

    # 说话人分段
    speaker_segments: List[SpeakerSegment]

    # 音频特征
    audio_features: AudioFeatures

    # 场景音频信息
    scene_audio_info: List[SceneAudioInfo]

@dataclass
class SpeakerEmbedding:
    """说话人嵌入"""
    speaker_id: str
    embedding: List[float]      # 嵌入向量
    confidence: float

    # 关联信息
    segments_count: int
    total_duration: float

    # 音频特征参考
    audio_features: AudioFeatures

@dataclass
class SpeakerSegment:
    """说话人分段"""
    segment_id: str
    speaker_id: str

    # 时间
    start_time: float
    end_time: float
    duration: float

    # 置信度
    confidence: float

    # 关联对白（如果有）
    dialogue_id: Optional[str] = None

@dataclass
class AudioFeatures:
    """音频特征"""
    # MFCC 特征
    mfcc_mean: np.ndarray
    mfcc_std: np.ndarray

    # 梅尔频谱
    mel_spectrogram_mean: np.ndarray
    mel_spectrogram_std: np.ndarray

    # 韵律特征
    pitch_mean: float
    pitch_std: float
    pitch_range: float

    energy_mean: float
    energy_std: float

    # 语音质量
    snr: float                # 信噪比
    zero_crossing_rate: float

@dataclass
class SceneAudioInfo:
    """场景音频信息"""
    scene_id: str

    # 环境音
    ambient_sound: str        # indoor, outdoor, crowd, traffic
    noise_level: str          # quiet, moderate, loud

    # 音乐检测
    has_music: bool
    music_mood: Optional[str] = None
    music_intensity: Optional[float] = None

    # 特殊音效
    has_sfx: bool
    sfx_types: List[str] = None
```

## 模块架构

```
┌─────────────────────────────────────────────────────────┐
│                         M05                               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐               │
│  │  音频提取器   │──────│  特征提取器   │               │
│  └──────────────┘      └──────────────┘               │
│         │                     │                             │
│         └──────────┬──────────┘                             │
│                    ▼                                       │
│         ┌────────────────────────┐                        │
│         │      说话人识别器          │                        │
│         │     (Diarization)         │                        │
│         └────────────────────────┘                        │
│                    │                                       │
│    ┌───────────────┴───────────────┐                      │
│    ▼                               ▼                       │
│ ┌──────────────┐         ┌──────────────┐                  │
│ │ 说话人嵌入   │         │  音频分类器   │                  │
│ │(Embedding)   │         │(音乐/音效)   │                  │
│ └──────────────┘         └──────────────┘                  │
│         │                         │                          │
│         └──────────┬──────────────┘                           │
│                    ▼                                        │
│         ┌────────────────────────┐                            │
│         │      场景音频关联          │                            │
│         └────────────────────────┘                            │
└─────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. 说话人识别器

```python
class SpeakerDiarization:
    """说话人识别"""

    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu
        self.pipeline = None

    async def initialize(self):
        """初始化模型"""
        from pyannote.audio import Pipeline

        self.pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=os.getenv("HF_TOKEN")
        )

        if self.use_gpu and torch.cuda.is_available():
            self.pipeline.to(torch.device("cuda"))

    async def process(
        self,
        audio_path: str,
        config: AudioAnalysisConfig
    ) -> Tuple[List[SpeakerSegment], Dict[str, AudioFeatures]]:
        """处理音频"""
        # 加载音频
        waveform, sample_rate = torchaudio.load(audio_path)

        # 执行说话人分段
        diarization = self.pipeline({
            "waveform": waveform,
            "sample_rate": sample_rate
        })

        # 转换为分段
        segments = self._convert_to_segments(diarization)

        # 为每个说话人提取特征
        features = await self._extract_features_per_speaker(
            waveform, sample_rate, segments, config
        )

        return segments, features

    def _convert_to_segments(
        self,
        diarization: Annotation
    ) -> List[SpeakerSegment]:
        """转换为分段列表"""
        segments = []
        segment_id = 0

        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(SpeakerSegment(
                segment_id=f"seg_{segment_id}",
                speaker_id=speaker,
                start_time=turn.start,
                end_time=turn.end,
                duration=turn.end - turn.start,
                confidence=0.9  # Pyannote 不提供置信度，使用默认值
            ))
            segment_id += 1

        return segments

    async def _extract_features_per_speaker(
        self,
        waveform: torch.Tensor,
        sample_rate: int,
        segments: List[SpeakerSegment],
        config: AudioAnalysisConfig
    ) -> Dict[str, AudioFeatures]:
        """为每个说话人提取特征"""
        features = {}

        # 按说话人分组
        speaker_segments = {}
        for seg in segments:
            if seg.speaker_id not in speaker_segments:
                speaker_segments[seg.speaker_id] = []
            speaker_segments[seg.speaker_id].append(seg)

        # 为每个说话人提取特征
        for speaker_id, segs in speaker_segments.items():
            # 提取该说话人的音频片段
            speaker_waveform = self._extract_speaker_audio(
                waveform, sample_rate, segs
            )

            # 计算特征
            features[speaker_id] = await self._compute_audio_features(
                speaker_waveform, sample_rate, config
            )

        return features

    def _extract_speaker_audio(
        self,
        waveform: torch.Tensor,
        sample_rate: int,
        segments: List[SpeakerSegment]
    ) -> torch.Tensor:
        """提取说话人的音频片段"""
        # 合并所有属于该说话人的片段
        segments_with_padding = []

        for seg in segments:
            start_sample = int(seg.start_time * sample_rate)
            end_sample = int(seg.end_time * sample_rate)
            segments_with_padding.append(
                waveform[:, start_sample:end_sample]
            )

        # 拼接
        return torch.cat(segments_with_padding, dim=1)

    async def _compute_audio_features(
        self,
        waveform: torch.Tensor,
        sample_rate: int,
        config: AudioAnalysisConfig
    ) -> AudioFeatures:
        """计算音频特征"""
        import librosa
        import numpy as np

        audio = waveform.squeeze().numpy()

        # MFCC 特征
        mfcc = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=13)
        mfcc_mean = np.mean(mfcc, axis=1)
        mfcc_std = np.std(mfcc, axis=1)

        # 梅尔频谱
        mel = librosa.feature.melspectrogram(y=audio, sr=sample_rate)
        mel_mean = np.mean(mel, axis=1)
        mel_std = np.std(mel, axis=1)

        # 音高特征
        pitches, magnitudes = librosa.piptrack(y=audio, sr=sample_rate)
        pitches = pitches[magnitudes > np.median(magnitudes)]
        pitch_mean = np.mean(pitches) if len(pitches) > 0 else 0
        pitch_std = np.std(pitches) if len(pitches) > 0 else 0
        pitch_range = np.max(pitches) - np.min(pitches) if len(pitches) > 0 else 0

        # 能量特征
        energy = librosa.feature.rms(y=audio)
        energy_mean = np.mean(energy)
        energy_std = np.std(energy)

        # 信噪比
        snr = self._calculate_snr(audio)

        # 过零率
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        zcr_mean = np.mean(zcr)

        return AudioFeatures(
            mfcc_mean=mfcc_mean,
            mfcc_std=mfcc_std,
            mel_spectrogram_mean=mel_mean,
            mel_spectrogram_std=mel_std,
            pitch_mean=float(pitch_mean),
            pitch_std=float(pitch_std),
            pitch_range=float(pitch_range),
            energy_mean=float(energy_mean),
            energy_std=float(energy_std),
            snr=float(snr),
            zero_crossing_rate=float(zcr_mean)
        )

    def _calculate_snr(self, audio: np.ndarray) -> float:
        """计算信噪比"""
        # 简化 SNR 计算
        signal_power = np.mean(audio ** 2)

        # 使用最低 10% 的功率作为噪声估计
        sorted_powers = np.sort(audio ** 2)
        noise_power = np.mean(sorted_powers[:len(sorted_powers)//10])

        if noise_power == 0:
            return float('inf')

        return 10 * np.log10(signal_power / noise_power)
```

### 2. 说话人嵌入提取器

```python
class SpeakerEmbeddingExtractor:
    """说话人嵌入提取器"""

    def __init__(self):
        self.model = None

    async def initialize(self):
        """初始化嵌入模型"""
        from speechbrain.inference.speaker import SpeakerRecognition

        self.model = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="pretrained_models"
        )

    async def extract(
        self,
        audio_path: str,
        segments: List[SpeakerSegment],
        speaker_features: Dict[str, AudioFeatures]
    ) -> List[SpeakerEmbedding]:
        """提取说话人嵌入"""
        embeddings = []

        for speaker_id in set(seg.speaker_id for seg in segments):
            # 提取该说话人的音频
            speaker_audio = self._extract_speaker_audio(
                audio_path, speaker_id, segments
            )

            # 计算嵌入
            embedding = self.model.encode_batch(
                speaker_audio.unsqueeze(0)
            ).squeeze().numpy()

            embeddings.append(SpeakerEmbedding(
                speaker_id=speaker_id,
                embedding=embedding.tolist(),
                confidence=0.9,
                segments_count=len([s for s in segments if s.speaker_id == speaker_id]),
                total_duration=sum(
                    s.duration for s in segments if s.speaker_id == speaker_id
                ),
                audio_features=speaker_features.get(speaker_id)
            ))

        return embeddings

    def _extract_speaker_audio(
        self,
        audio_path: str,
        speaker_id: str,
        segments: List[SpeakerSegment]
    ) -> torch.Tensor:
        """提取说话人音频"""
        # 使用 torchaudio 加载
        waveform, sample_rate = torchaudio.load(audio_path)

        # 提取该说话人的所有片段
        speaker_segments = [s for s in segments if s.speaker_id == speaker_id]

        segments_tensor = []
        for seg in speaker_segments:
            start_sample = int(seg.start_time * sample_rate)
            end_sample = int(seg.end_time * sample_rate)
            segments_tensor.append(
                waveform[:, start_sample:end_sample]
            )

        # 拼接并填充到固定长度
        max_length = max(seg.shape[1] for seg in segments_tensor)
        padded_segments = []

        for seg in segments_tensor:
            if seg.shape[1] < max_length:
                padding = max_length - seg.shape[1]
                seg = torch.nn.functional.pad(seg, (0, padding))
            padded_segments.append(seg)

        return torch.cat(padded_segments, dim=1)
```

### 3. 音频分类器

```python
class AudioClassifier:
    """音频分类器"""

    async def classify_scene_audio(
        self,
        audio_path: str,
        scene_timeline: SceneTimeline
    ) -> List[SceneAudioInfo]:
        """分类场景音频"""
        scene_audio_info = []

        for scene in scene_timeline.scenes:
            # 提取场景音频
            scene_audio = self._extract_scene_audio(audio_path, scene)

            # 分类环境音
            ambient = await self._classify_ambient(scene_audio)

            # 检测音乐
            has_music, music_mood, music_intensity = await self._detect_music(scene_audio)

            # 检测音效
            has_sfx, sfx_types = await self._detect_sfx(scene_audio)

            scene_audio_info.append(SceneAudioInfo(
                scene_id=scene.id,
                ambient_sound=ambient,
                noise_level=self._estimate_noise_level(scene_audio),
                has_music=has_music,
                music_mood=music_mood,
                music_intensity=music_intensity,
                has_sfx=has_sfx,
                sfx_types=sfx_types
            ))

        return scene_audio_info

    def _extract_scene_audio(
        self,
        audio_path: str,
        scene: Scene
    ) -> torch.Tensor:
        """提取场景音频"""
        import torchaudio

        waveform, sample_rate = torchaudio.load(audio_path)

        start_sample = int(scene.start_time * sample_rate)
        end_sample = int(scene.end_time * sample_rate)

        return waveform[:, start_sample:end_sample]

    async def _classify_ambient(self, audio: torch.Tensor) -> str:
        """分类环境音"""
        # 简化实现：基于音频特征分类
        rms = torch.sqrt(torch.mean(audio ** 2))

        if rms < 0.01:
            return "quiet"
        elif rms < 0.05:
            return "indoor"
        elif rms < 0.1:
            return "outdoor"
        else:
            return "crowd"  # 或 traffic

    async def _detect_music(
        self,
        audio: torch.Tensor
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """检测音乐"""
        # 使用 librosa 检测音乐特征
        import librosa
        import numpy as np

        y = audio.squeeze().numpy()

        # 检测节奏
        tempo, _ = librosa.beat.beat_track(y=y)

        # 检测和声
        chromagram = librosa.feature.chroma_stft(y=y)
        chord_strength = np.mean(chromagram)

        # 简单判断：有节奏+和声 = 音乐
        has_music = chord_strength > 0.5

        mood = None
        intensity = None

        if has_music:
            # 推断情绪
            if tempo > 120:
                mood = "energetic"
            elif tempo < 60:
                mood = "calm"
            else:
                mood = "neutral"

            intensity = float(chord_strength)

        return has_music, mood, intensity

    async def _detect_sfx(
        self,
        audio: torch.Tensor
    ) -> Tuple[bool, List[str]]:
        """检测音效"""
        # 简化实现：检测瞬态信号
        import numpy as np

        y = audio.squeeze().numpy()
        onset_frames = librosa.onset.onset_detect(y=y)

        # 高频瞬态 = 音效
        has_sfx = len(onset_frames) > 10

        sfx_types = []
        if has_sfx:
            # 简单分类
            sfx_types = ["impact", "whoosh"]  # 示例

        return has_sfx, sfx_types

    def _estimate_noise_level(self, audio: torch.Tensor) -> str:
        """估计噪音水平"""
        rms = torch.sqrt(torch.mean(audio ** 2))

        if rms < 0.01:
            return "quiet"
        elif rms < 0.05:
            return "moderate"
        else:
            return "loud"
```

## 错误处理

### 错误代码

| 代码 | 描述 | 可重试 |
|------|------|--------|
| M005-001 | 音频提取失败 | 是 |
| M005-002 | 说话人识别失败 | 是 |
| M005-003 | 嵌入提取失败 | 是 |
| M005-004 | GPU 内存不足 | 是 |
| M005-005 | 模型加载失败 | 是 |

### 降级策略

1. **GPU 不足**: 切换到 CPU
2. **说话人识别失败**: 使用音频特征聚类
3. **嵌入提取失败**: 使用 MFCC 特征替代

## 测试要点

1. 各种音频质量测试
2. 不同说话人数测试
3. 背景音乐干扰测试
4. 性能测试（处理速度）
5. 准确性测试

## 后续模块依赖

M05 的输出被以下模块使用：
- **M04**: 说话人嵌入用于人物聚类
- **M06**: 说话人分段用于人物映射
- **M07**: 场景音频信息用于对白处理
- **M10**: 音频分类用于混音
