# M05: Audio & Scene Analysis - 音频与场景分析

## 概述

M05 负责分析音频和视频内容，提取说话人嵌入、音频特征、场景信息等，为后续的人物识别和音色克隆提供基础数据。

## 核心职责

1. **说话人识别 (Speaker Diarization)**: 识别音频中的不同说话人
2. **说话人嵌入提取**: 提取每个说话人的声纹特征向量
3. **音频特征提取**: 提取音高、能量、语速等音频特征
4. **场景分析**: 识别视频场景边界和类型
5. **情感分析**: 识别对白的情感倾向
6. **VAD (Voice Activity Detection)**: 语音活动检测

## 输入/输出

### 输入 Artifact

- `source_video` (来自 M01): 原始视频
- `audio_track` (来自 M01): 音频轨道
- `subtitle_timeline` (来自 M03): 字幕时间轴 (可选)

### 输出 Artifact

- `speaker_embeddings`: 说话人嵌入向量
- `audio_features`: 音频特征
- `scene_timeline`: 场景时间轴
- `speaker_segments`: 说话人分段
- `emotion_tags`: 情感标签

## 技术栈

- **语言**: Python 3.11+
- **说话人识别**: pyannote.audio
- **音频处理**: librosa, pydub
- **视频处理**: ffmpeg-python, opencv-python
- **嵌入模型**: speechbrain, ECAPA-TDNN
- **情感识别**: wav2vec2-emotion

## 数据结构

### SpeakerEmbedding

```python
@dataclass
class SpeakerEmbedding:
    speaker_id: str           # 临时说话人 ID
    embedding: List[float]    # 嵌入向量 (通常 192-512 维)
    segments: List[SpeakerSegment]

@dataclass
class SpeakerSegment:
    start_time: float         # 开始时间 (秒)
    end_time: float           # 结束时间 (秒)
    confidence: float         # 置信度
    text: Optional[str] = None  # 对应文本 (如果有字幕)
```

### AudioFeatures

```python
@dataclass
class AudioFeatures:
    speaker_id: str

    # 音高
    pitch_mean: float
    pitch_std: float
    pitch_range: float

    # 能量
    energy_mean: float
    energy_std: float

    # 语速
    speaking_rate: float      # 音节/秒
    pause_rate: float         # 停顿频率

    # 频谱
    spectral_centroid_mean: float
    spectral_bandwidth_mean: float
    spectral_rolloff_mean: float

    # MFCC
    mfcc_mean: List[float]    # MFCC 均值
    mfcc_std: List[float]     # MFCC 标准差
```

### SceneTimeline

```python
@dataclass
class Scene:
    id: str
    start_time: float
    end_time: float
    scene_type: SceneType
    location: Optional[str] = None
    characters: List[str] = None  # 场景中出现的人物

class SceneType(Enum):
    INT_INTERIOR = "interior"      # 室内
    INT_EXTERIOR = "exterior"      # 室外
    INT_DAY = "day"               # 白天
    INT_NIGHT = "night"           # 夜晚
    INT_TRANSITION = "transition" # 过渡场景
```

### EmotionTag

```python
@dataclass
class EmotionTag:
    segment_id: str
    emotion: Emotion
    intensity: float        # 0.0-1.0
    confidence: float
```

## 核心算法

### 1. 说话人识别 (Speaker Diarization)

使用 pyannote.audio 进行说话人分离：

```python
from pyannote.audio import Pipeline

class SpeakerDiarization:
    def __init__(self, model_name: str = "pyannote/speaker-diarization-3.1"):
        self.pipeline = Pipeline.from_pretrained(model_name)

    async def diarize(
        self,
        audio_path: str
    ) -> List[SpeakerSegment]:
        """说话人分离"""
        diarization = self.pipeline(audio_path)

        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(SpeakerSegment(
                start_time=turn.start,
                end_time=turn.end,
                confidence=0.9,  # 模型默认置信度
                speaker=speaker
            ))

        return segments
```

### 2. 说话人嵌入提取

使用 speechbrain ECAPA-TDNN 模型：

```python
from speechbrain.inference.speaker import SpeakerRecognition

class SpeakerEmbeddingExtractor:
    def __init__(self):
        self.model = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="pretrained_models/ecapa-tdnn"
        )

    async def extract(
        self,
        audio_path: str,
        segments: List[SpeakerSegment]
    ) -> List[SpeakerEmbedding]:
        """提取说话人嵌入"""
        embeddings = []

        # 按说话人分组
        speaker_segments = self._group_by_speaker(segments)

        for speaker_id, segs in speaker_segments.items():
            # 拼接该说话人的所有片段
            combined_audio = self._concatenate_segments(
                audio_path, segs
            )

            # 提取嵌入
            embedding = self.model.encode_batch(combined_audio)
            embedding = embedding.squeeze().tolist()

            embeddings.append(SpeakerEmbedding(
                speaker_id=speaker_id,
                embedding=embedding,
                segments=segs
            ))

        return embeddings

    def _group_by_speaker(
        self,
        segments: List[SpeakerSegment]
    ) -> Dict[str, List[SpeakerSegment]]:
        """按说话人分组"""
        groups = {}
        for seg in segments:
            if seg.speaker not in groups:
                groups[seg.speaker] = []
            groups[seg.speaker].append(seg)
        return groups
```

### 3. 音频特征提取

使用 librosa 提取音频特征：

```python
import librosa

class AudioFeatureExtractor:
    async def extract(
        self,
        audio_path: str,
        segments: List[SpeakerSegment]
    ) -> List[AudioFeatures]:
        """提取音频特征"""
        # 加载音频
        y, sr = librosa.load(audio_path, sr=22050)

        features = []

        for segment in segments:
            # 提取片段
            start_sample = int(segment.start_time * sr)
            end_sample = int(segment.end_time * sr)
            y_seg = y[start_sample:end_sample]

            # 提取特征
            pitch = self._extract_pitch(y_seg, sr)
            energy = self._extract_energy(y_seg)
            spectral = self._extract_spectral(y_seg, sr)
            mfcc = self._extract_mfcc(y_seg, sr)

            # 计算语速
            speaking_rate = self._calculate_speaking_rate(segment)

            features.append(AudioFeatures(
                speaker_id=segment.speaker,
                pitch_mean=pitch['mean'],
                pitch_std=pitch['std'],
                pitch_range=pitch['range'],
                energy_mean=energy['mean'],
                energy_std=energy['std'],
                speaking_rate=speaking_rate,
                pause_rate=energy['zero_crossing_rate'],
                spectral_centroid_mean=spectral['centroid'],
                spectral_bandwidth_mean=spectral['bandwidth'],
                spectral_rolloff_mean=spectral['rolloff'],
                mfcc_mean=mfcc['mean'],
                mfcc_std=mfcc['std']
            ))

        return features

    def _extract_pitch(
        self,
        y: np.ndarray,
        sr: int
    ) -> Dict:
        """提取音高"""
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_values = []

        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)

        if not pitch_values:
            return {'mean': 0, 'std': 0, 'range': 0}

        return {
            'mean': np.mean(pitch_values),
            'std': np.std(pitch_values),
            'range': np.max(pitch_values) - np.min(pitch_values)
        }

    def _extract_energy(self, y: np.ndarray) -> Dict:
        """提取能量"""
        rms = librosa.feature.rms(y=y)[0]
        return {
            'mean': np.mean(rms),
            'std': np.std(rms),
            'zero_crossing_rate': np.mean(librosa.feature.zero_crossing_rate(y)[0])
        }

    def _extract_spectral(
        self,
        y: np.ndarray,
        sr: int
    ) -> Dict:
        """提取频谱特征"""
        return {
            'centroid': np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0]),
            'bandwidth': np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]),
            'rolloff': np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)[0])
        }

    def _extract_mfcc(
        self,
        y: np.ndarray,
        sr: int
    ) -> Dict:
        """提取 MFCC"""
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        return {
            'mean': np.mean(mfcc, axis=1).tolist(),
            'std': np.std(mfcc, axis=1).tolist()
        }
```

### 4. 场景分析

使用计算机视觉检测场景边界：

```python
import cv2
from sklearn.cluster import KMeans

class SceneAnalyzer:
    async def detect_scenes(
        self,
        video_path: str,
        threshold: float = 30.0
    ) -> List[Scene]:
        """检测场景边界"""
        cap = cv2.VideoCapture(video_path)

        # 提取关键帧
        frames = self._extract_keyframes(cap, interval=1.0)

        # 计算帧间差异
        diff_scores = self._calculate_frame_differences(frames)

        # 检测边界
        boundaries = self._detect_boundaries(diff_scores, threshold)

        # 分类场景
        scenes = []
        for i, (start, end) in enumerate(zip([0] + boundaries, boundaries + [len(frames)])):
            scene_type = self._classify_scene_type(frames[start:end])
            scenes.append(Scene(
                id=f"scene_{i}",
                start_time=start,
                end_time=end,
                scene_type=scene_type
            ))

        cap.release()
        return scenes

    def _extract_keyframes(
        self,
        cap: cv2.VideoCapture,
        interval: float = 1.0
    ) -> List[np.ndarray]:
        """提取关键帧"""
        frames = []
        fps = cap.get(cv2.CAP_PROP_FPS)

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % int(fps * interval) == 0:
                frames.append(frame)

            frame_idx += 1

        return frames

    def _calculate_frame_differences(
        self,
        frames: List[np.ndarray]
    ) -> List[float]:
        """计算帧间差异"""
        diffs = []

        for i in range(len(frames) - 1):
            # 转换为灰度
            gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)

            # 计算差异
            diff = cv2.absdiff(gray1, gray2)
            score = np.mean(diff)

            diffs.append(score)

        return diffs

    def _detect_boundaries(
        self,
        diff_scores: List[float],
        threshold: float
    ) -> List[int]:
        """检测场景边界"""
        boundaries = []

        for i, score in enumerate(diff_scores):
            if score > threshold:
                boundaries.append(i + 1)

        return boundaries

    def _classify_scene_type(
        self,
        frames: List[np.ndarray]
    ) -> SceneType:
        """分类场景类型"""
        # 简化处理：分析亮度和颜色
        brightness = np.mean([np.mean(f) for f in frames])

        if brightness < 50:
            return SceneType.INT_NIGHT
        elif brightness > 150:
            return SceneType.INT_DAY
        else:
            return SceneType.INT_INTERIOR
```

### 5. 情感识别

使用预训练的情感识别模型：

```python
from transformers import pipeline

class EmotionRecognizer:
    def __init__(self):
        self.classifier = pipeline(
            "audio-classification",
            model="superb/wav2vec2-base-superb-er"
        )

    async def recognize_emotions(
        self,
        audio_path: str,
        segments: List[SpeakerSegment]
    ) -> List[EmotionTag]:
        """识别情感"""
        import librosa
        y, sr = librosa.load(audio_path, sr=16000)

        tags = []

        for seg in segments:
            # 提取片段
            start_sample = int(seg.start_time * sr)
            end_sample = int(seg.end_time * sr)
            y_seg = y[start_sample:end_sample]

            # 预测情感
            result = self.classifier(y_seg)

            # 获取最高置信度的情感
            top_result = result[0]
            emotion = self._map_emotion(top_result['label'])

            tags.append(EmotionTag(
                segment_id=f"{seg.start_time}-{seg.end_time}",
                emotion=emotion,
                intensity=top_result['score'],
                confidence=top_result['score']
            ))

        return tags

    def _map_emotion(self, label: str) -> Emotion:
        """映射情感标签"""
        mapping = {
            'hap': Emotion.HAPPY,
            'sad': Emotion.SAD,
            'ang': Emotion.ANGRY,
            'fea': Emotion.FEARFUL,
            'dis': Emotion.DISGUSTED,
            'sur': Emotion.SURPRISED,
            'neu': Emotion.NEUTRAL
        }
        return mapping.get(label, Emotion.NEUTRAL)
```

## 目录结构

```
src/filmdub/workers/audio_scene_analysis/
├── __init__.py
├── main.py                 # Worker 入口
├── config.py               # 配置
├── diarization.py          # 说话人识别
├── embedding.py            # 嵌入提取
├── audio_features.py       # 音频特征
├── scene_analysis.py       # 场景分析
├── emotion_recognition.py  # 情感识别
└── tests/
    ├── test_diarization.py
    ├── test_embedding.py
    └── test_audio_features.py
```

## 配置示例

```python
@dataclass
class M05Config:
    # 说话人识别
    diarization_model: str = "pyannote/speaker-diarization-3.1"
    diarization_batch_size: int = 32

    # 嵌入提取
    embedding_model: str = "speechbrain/spkrec-ecapa-voxceleb"
    embedding_dim: int = 192

    # 情感识别
    emotion_model: str = "superb/wav2vec2-base-superb-er"

    # 场景检测
    scene_threshold: float = 30.0
    keyframe_interval: float = 1.0

    # 音频处理
    sample_rate: int = 22050
    hop_length: int = 512
    n_mfcc: int = 13
```

## 依赖模块

- **M01**: 获取原始视频和音频
- **M03**: 获取字幕时间轴（可选）

## 后续模块依赖

M05 的输出被以下模块使用：
- **M04**: 说话人嵌入用于人物聚类
- **M06**: 说话人信息用于映射到人物
- **M07**: 情感标签用于对白智能处理
- **M08**: 情感信息用于韵律规划

## 实现优先级

### Phase 1: 核心功能 (高优先级)
1. 说话人识别
2. 说话人嵌入提取
3. 音频特征提取

### Phase 2: 场景分析 (中优先级)
1. 场景边界检测
2. 场景类型分类

### Phase 3: 情感识别 (中优先级)
1. 情感识别模型集成
2. 情感映射和标签

### Phase 4: 优化 (低优先级)
1. 批量处理优化
2. GPU 加速
3. 缓存机制

## 测试要点

1. 说话人识别准确性测试
2. 不同语言和口音的鲁棒性
3. 音频特征提取的正确性
4. 场景边界检测准确性
5. 情感识别准确性

## 参考 ADR

- ADR 0016: M05 音频与场景分析
- ADR 0001: 基于 Artifact 的模块架构
