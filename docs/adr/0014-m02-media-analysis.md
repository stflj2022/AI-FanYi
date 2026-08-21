# ADR 0014: M02 项目研究与身份解析模块设计

## 状态

设计中

## 上下文

M02 负责分析原始视频的技术属性、提取场景信息、检测镜头变化，为后续处理提供基础数据。

## 核心职责

1. **媒体分析**: 提取视频编码、分辨率、FPS、音频轨信息
2. **场景检测**: 识别场景边界、黑屏检测
3. **镜头检测**: 识别镜头切换
4. **时间轴分析**: 建立准确的时间轴
5. **音视频预处理**: 必要的格式转换和预处理

## 输入/输出

### 输入

```python
@dataclass
class M02Input:
    """M02 输入数据结构"""
    project_id: uuid.UUID
    job_id: uuid.UUID

    # 来自 M01 的源视频 Artifact
    source_video_artifact_id: uuid.UUID

    # 分析配置
    config: MediaAnalysisConfig

@dataclass
class MediaAnalysisConfig:
    """媒体分析配置"""
    # 场景检测
    detect_scenes: bool = True
    scene_threshold: float = 0.3  # 场景变化阈值

    # 镜头检测
    detect_shots: bool = True
    shot_min_duration: float = 0.5  # 最小镜头时长（秒）

    # 黑屏检测
    detect_black_frames: bool = True
    black_threshold: float = 0.1  # 黑屏阈值

    # 音频分析
    analyze_audio: bool = True
    detect_silence: bool = True
    silence_threshold: float = -40.0  # dB

    # 性能
    use_gpu: bool = True
    batch_processing: bool = True
```

### 输出

```python
@dataclass
class M02Output:
    """M02 输出数据结构"""
    # 媒体分析结果
    media_analysis: MediaAnalysis

    # 场景时间轴
    scene_timeline: SceneTimeline

    # 音频分析
    audio_analysis: AudioAnalysis

    # 分析统计
    statistics: AnalysisStatistics

@dataclass
class MediaAnalysis:
    """媒体分析结果"""
    # 视频信息
    video_info: VideoInfo

    # 时间轴信息
    timeline: TimelineInfo

    # 预处理后的视频（如果有转换）
    processed_video_artifact_id: Optional[uuid.UUID] = None

@dataclass
class VideoInfo:
    """详细视频信息"""
    format: str                    # 容器格式
    video_codec: str               # 视频编码
    audio_codecs: List[str]        # 音频编码列表

    # 分辨率
    width: int
    height: int
    aspect_ratio: str             # 宽高比

    # 帧率
    fps: float
    fps_nom: int                  # 分子
    fps_den: int                  # 分母

    # 时长
    duration_seconds: float
    duration_frames: int

    # 比特率
    video_bitrate: int             # bps
    audio_bitrate: int             # bps
    total_bitrate: int

    # 色彩
    color_space: str               # YUV, RGB
    bit_depth: int                 # 8, 10, 12

    # 音轨
    audio_tracks: List[AudioTrackDetail]

@dataclass
class AudioTrackDetail:
    """音轨详细信息"""
    index: int
    codec: str
    language: str
    channels: int
    sample_rate: int
    bit_depth: int
    bitrate: int
    duration: float

    # 内容分析
    has_dialogue: bool
    has_music: bool
    has_sfx: bool

@dataclass
class TimelineInfo:
    """时间轴信息"""
    total_duration: float
    frame_count: int

    # 章节标记
    chapters: List[Chapter] = None

    # 信任度（如果有时码问题）
    timecode_confidence: float = 1.0

@dataclass
class Chapter:
    """章节标记"""
    start_time: float
    end_time: float
    title: Optional[str] = None

@dataclass
class SceneTimeline:
    """场景时间轴"""
    scenes: List[Scene]

    # 统计
    total_scenes: int
    average_scene_duration: float

@dataclass
class Scene:
    """场景"""
    id: str
    start_time: float
    end_time: float
    duration: float

    # 场景特征
    location: Optional[str] = None   # 室内/室外
    time_of_day: Optional[str] = None  # 早晨/晚上等
    shots: List[Shot] = None

    # 视觉特征
    brightness: Optional[float] = None
    color_palette: Optional[List[str]] = None
    dominant_colors: Optional[List[str]] = None

@dataclass
class Shot:
    """镜头"""
    id: str
    start_time: float
    end_time: float
    duration: float

    # 镜头类型
    shot_type: Optional[str] = None    # close-up, medium, long
    camera_movement: Optional[str] = None  # pan, tilt, zoom, static

@dataclass
class AudioAnalysis:
    """音频分析结果"""
    tracks: List[AudioTrackAnalysis]

    # 音量分析
    loudness_stats: LoudnessStats

    # 对白区域
    dialogue_regions: List[DialogueRegion]

    # 音乐区域
    music_regions: List[MusicRegion]

    # 静音区域
    silence_regions: List[SilenceRegion]

@dataclass
class AudioTrackAnalysis:
    """音轨分析"""
    track_index: int
    language: str

    # 频谱特征
    spectral_centroid: float
    spectral_rolloff: float
    zero_crossing_rate: float

    # 能量分布
    energy_distribution: List[float]

@dataclass
class LoudnessStats:
    """音量统计"""
    integrated_lufs: float         # 综合响度
    momentary_lufs: List[float]     # 瞬时响度
    short_term_lufs: List[float]    # 短期响度

    peak_db: float                  # 峰值
    range_db: float                 # 动态范围

@dataclass
class DialogueRegion:
    """对白区域"""
    start_time: float
    end_time: float
    speakers: List[str] = None      # 说话人（初步）
    confidence: float = 0.0

@dataclass
class MusicRegion:
    """音乐区域"""
    start_time: float
    end_time: float
    mood: Optional[str] = None
    intensity: Optional[float] = None

@dataclass
class SilenceRegion:
    """静音区域"""
    start_time: float
    end_time: float
    duration: float
```

## 模块架构

```
┌─────────────────────────────────────────────────────────┐
│                         M02                               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐               │
│  │  视频分析器   │──────│  音频分析器   │               │
│  └──────────────┘      └──────────────┘               │
│         │                     │                             │
│         └──────────┬──────────┘                             │
│                    ▼                                       │
│         ┌────────────────────────┐                        │
│         │      场景检测器          │                        │
│         │   (场景/镜头/黑屏)        │                        │
│         └────────────────────────┘                        │
│                    │                                       │
│                    ▼                                       │
│         ┌────────────────────────┐                        │
│         │      时间轴构建          │                        │
│         │   (章节/标记/信任度)       │                        │
│         └────────────────────────┘                        │
│                    │                                       │
│                    ▼                                       │
│         ┌────────────────────────┐                        │
│         │      数据整合            │                        │
│         └────────────────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. 视频分析器

```python
class VideoAnalyzer:
    """视频分析器"""

    def __init__(self, artifact_registry: ArtifactRegistry):
        self.artifact_registry = artifact_registry

    async def analyze(
        self,
        video_artifact_id: uuid.UUID,
        config: MediaAnalysisConfig
    ) -> VideoInfo:
        """分析视频文件"""
        # 下载视频
        video_path = await self._download_video(video_artifact_id)

        # 使用 FFmpeg 分析
        probe_data = await self._ffprobe(video_path)

        # 提取详细信息
        video_info = self._extract_video_info(probe_data)

        # 如果需要预处理
        if self._needs_preprocessing(video_info, config):
            processed_id = await self._preprocess_video(
                video_path, video_info, config
            )
            video_info.processed_artifact_id = processed_id

        return video_info

    async def _ffprobe(self, video_path: str) -> Dict:
        """使用 FFprobe 分析"""
        import subprocess
        import json

        cmd = [
            'ffprobe',
            '-v', 'error',
            '-print_format', 'json',
            '-show_streams',
            '-show_format',
            video_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFprobe failed: {result.stderr.decode()}")

        return json.loads(result.stdout)

    def _extract_video_info(self, probe_data: Dict) -> VideoInfo:
        """从 FFprobe 数据提取信息"""
        # 查找视频流
        video_stream = None
        audio_streams = []

        for stream in probe_data['streams']:
            if stream['codec_type'] == 'video' and video_stream is None:
                video_stream = stream
            elif stream['codec_type'] == 'audio':
                audio_streams.append(stream)

        if not video_stream:
            raise ValueError("No video stream found")

        # 计算帧率
        fps_str = video_stream.get('r_frame_rate', '25/1')
        nom, den = map(int, fps_str.split('/'))
        fps = nom / den

        # 计算时长
        duration = float(probe_data['format'].get('duration', 0))

        return VideoInfo(
            format=probe_data['format'].get('format_name', 'unknown'),
            video_codec=video_stream.get('codec_name', 'unknown'),
            audio_codecs=[s.get('codec_name') for s in audio_streams],
            width=int(video_stream.get('width', 0)),
            height=int(video_stream.get('height', 0)),
            aspect_ratio=self._calculate_aspect_ratio(
                video_stream.get('width', 0),
                video_stream.get('height', 0)
            ),
            fps=fps,
            fps_nom=nom,
            fps_den=den,
            duration_seconds=duration,
            duration_frames=int(duration * fps),
            video_bitrate=int(video_stream.get('bit_rate', 0)),
            audio_bitrate=sum(
                int(s.get('bit_rate', 0)) for s in audio_streams
            ),
            total_bitrate=int(probe_data['format'].get('bit_rate', 0)),
            color_space=video_stream.get('pix_fmt', 'unknown'),
            bit_depth=int(video_stream.get('bits_per_raw_sample', 8)),
            audio_tracks=self._extract_audio_tracks(audio_streams)
        )

    def _calculate_aspect_ratio(self, width: int, height: int) -> str:
        """计算宽高比"""
        if height == 0:
            return "unknown"

        # 计算最大公约数
        from math import gcd
        divisor = gcd(width, height)

        return f"{width//divisor}:{height//divisor}"

    def _extract_audio_tracks(self, streams: List[Dict]) -> List[AudioTrackDetail]:
        """提取音轨信息"""
        tracks = []

        for i, stream in enumerate(streams):
            tracks.append(AudioTrackDetail(
                index=i,
                codec=stream.get('codec_name', 'unknown'),
                language=stream.get('tags', {}).get('language', 'und'),
                channels=int(stream.get('channels', 2)),
                sample_rate=int(stream.get('sample_rate', 48000)),
                bit_depth=int(stream.get('bits_per_sample', 16)),
                bitrate=int(stream.get('bit_rate', 0)),
                duration=float(stream.get('duration', 0)),
                has_dialogue=False,  # 将在音频分析中确定
                has_music=False,
                has_sfx=False
            ))

        return tracks

    def _needs_preprocessing(
        self,
        video_info: VideoInfo,
        config: MediaAnalysisConfig
    ) -> bool:
        """判断是否需要预处理"""
        # 检查编码兼容性
        if video_info.video_codec not in ['h264', 'h265', 'hevc']:
            return True

        # 检查分辨率
        if video_info.height > 2160:  # 超过 4K
            return True

        # 检查帧率
        if video_info.fps < 24 or video_info.fps > 60:
            return True

        return False

    async def _preprocess_video(
        self,
        video_path: str,
        video_info: VideoInfo,
        config: MediaAnalysisConfig
    ) -> uuid.UUID:
        """预处理视频"""
        import subprocess

        output_path = f"/tmp/{uuid.uuid4()}.mp4"

        # FFmpeg 转换命令
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ar', '48000',
            '-vf', 'scale=-2:1080',  # 限制到 1080p
            '-r', '30',  # 统一帧率
            output_path
        ]

        subprocess.run(cmd, check=True, timeout=600)

        # 上传预处理后的视频
        return await self._upload_processed_video(output_path)
```

### 2. 场景检测器

```python
class SceneDetector:
    """场景检测器"""

    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu

    async def detect_scenes(
        self,
        video_path: str,
        config: MediaAnalysisConfig
    ) -> SceneTimeline:
        """检测场景"""
        if config.use_gpu and self._check_gpu_available():
            return await self._detect_scenes_gpu(video_path, config)
        else:
            return await self._detect_scenes_cpu(video_path, config)

    async def _detect_scenes_gpu(
        self,
        video_path: str,
        config: MediaAnalysisConfig
    ) -> SceneTimeline:
        """使用 GPU 进行场景检测"""
        import cv2
        import numpy as np

        cap = cv2.VideoCapture(video_path)

        scenes = []
        prev_hist = None
        scene_start = 0
        frame_count = 0
        fps = cap.get(cv2.CAP_PROP_FPS)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 计算直方图
            hist = cv2.calcHist([frame], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist = cv2.normalize(hist, hist).flatten()

            # 计算与前一帧的差异
            if prev_hist is not None:
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)

                if diff < config.scene_threshold:  # 场景切换
                    current_time = frame_count / fps

                    if len(scenes) > 0:
                        scenes[-1].end_time = current_time
                        scenes[-1].duration = current_time - scenes[-1].start_time

                    scenes.append(Scene(
                        id=f"scene_{len(scenes)}",
                        start_time=current_time,
                        end_time=None,
                        duration=0
                    ))
                    scene_start = frame_count

            prev_hist = hist
            frame_count += 1

        cap.release()

        # 设置最后一个场景的结束时间
        if scenes:
            scenes[-1].end_time = frame_count / fps
            scenes[-1].duration = scenes[-1].end_time - scenes[-1].start_time

        return SceneTimeline(
            scenes=scenes,
            total_scenes=len(scenes),
            average_scene_duration=sum(s.duration for s in scenes) / len(scenes) if scenes else 0
        )

    async def _detect_scenes_cpu(
        self,
        video_path: str,
        config: MediaAnalysisConfig
    ) -> SceneTimeline:
        """使用 CPU 进行场景检测（简化版）"""
        # 使用 PySceneDetect
        from scenedetect import detect, ContentDetector

        scene_list = detect(
            video_path,
            ContentDetector(
                threshold=config.scene_threshold,
                min_scene_len=config.shot_min_duration * 1000  # ms
            )
        )

        scenes = []
        for i, (start, end) in enumerate(scene_list):
            scenes.append(Scene(
                id=f"scene_{i}",
                start_time=start.get_seconds(),
                end_time=end.get_seconds(),
                duration=end.get_seconds() - start.get_seconds()
            ))

        return SceneTimeline(
            scenes=scenes,
            total_scenes=len(scenes),
            average_scene_duration=sum(s.duration for s in scenes) / len(scenes) if scenes else 0
        )

    def _check_gpu_available(self) -> bool:
        """检查 GPU 是否可用"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
```

### 3. 音频分析器

```python
class AudioAnalyzer:
    """音频分析器"""

    def __init__(self):
        pass

    async def analyze(
        self,
        video_path: str,
        config: MediaAnalysisConfig
    ) -> AudioAnalysis:
        """分析音频"""
        # 提取音频
        audio_path = await self._extract_audio(video_path)

        # 分析音轨
        tracks = await self._analyze_tracks(audio_path)

        # 分析音量
        loudness = await self._analyze_loudness(audio_path)

        # 检测对白区域
        dialogue = await self._detect_dialogue_regions(audio_path)

        # 检测音乐区域
        music = await self._detect_music_regions(audio_path)

        # 检测静音区域
        silence = await self._detect_silence_regions(
            audio_path, config.silence_threshold
        )

        return AudioAnalysis(
            tracks=tracks,
            loudness_stats=loudness,
            dialogue_regions=dialogue,
            music_regions=music,
            silence_regions=silence
        )

    async def _extract_audio(self, video_path: str) -> str:
        """提取音频"""
        import subprocess

        audio_path = f"/tmp/{uuid.uuid4()}.wav"

        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '48000',
            '-ac', '2',
            audio_path
        ]

        subprocess.run(cmd, check=True, timeout=600)

        return audio_path

    async def _analyze_loudness(self, audio_path: str) -> LoudnessStats:
        """分析音量"""
        # 使用 pyloudnorm 分析响度
        from pyloudnorm import Meter

        meter = Meter(srate=48000)  # 假设采样率

        # 读取音频
        import librosa
        audio, sr = librosa.load(audio_path, sr=48000)

        # 计算响度
        loudness = meter.integrated_loudness(audio)

        return LoudnessStats(
            integrated_lufs=loudness,
            momentary_lufs=[],
            short_term_lufs=[],
            peak_db=0.0,
            range_db=0.0
        )

    async def _detect_dialogue_regions(
        self,
        audio_path: str
    ) -> List[DialogueRegion]:
        """检测对白区域"""
        # 使用 VAD (Voice Activity Detection)
        import webrtcvad

        vad = webrtcvad.Vad(2)  # 敏感度 0-3

        # 读取音频
        import librosa
        audio, sr = librosa.load(audio_path, sr=16000)

        # 分帧处理
        frame_duration = 30  # ms
        frame_size = int(sr * frame_duration / 1000)

        regions = []
        in_speech = False
        region_start = 0

        for i in range(0, len(audio), frame_size):
            frame = audio[i:i+frame_size]

            # 确保帧长足够
            if len(frame) < frame_size:
                continue

            # VAD 检测
            is_speech = vad.is_speech(
                (frame * 32767).astype(np.int16).tobytes(),
                sr,
                frame_duration
            )

            if is_speech and not in_speech:
                region_start = i / sr
                in_speech = True

            elif not is_speech and in_speech:
                region_end = i / sr
                if region_end - region_start > 0.5:  # 至少 0.5 秒
                    regions.append(DialogueRegion(
                        start_time=region_start,
                        end_time=region_end,
                        confidence=0.8
                    ))
                in_speech = False

        return regions

    async def _detect_silence_regions(
        self,
        audio_path: str,
        threshold_db: float
    ) -> List[SilenceRegion]:
        """检测静音区域"""
        import librosa

        audio, sr = librosa.load(audio_path, sr=None)

        # 计算功率
        frame_length = 2048
        hop_length = 512

        rms = librosa.feature.rms(
            y=audio,
            frame_length=frame_length,
            hop_length=hop_length
        )[0]

        # 转换为 dB
        rms_db = 20 * np.log10(rms + 1e-10)

        # 检测低于阈值的区域
        silence_mask = rms_db < threshold_db

        regions = []
        in_silence = False
        silence_start = 0

        time_points = librosa.frames_to_time(
            np.arange(len(rms_db)),
            sr=sr,
            hop_length=hop_length
        )

        for i, is_silent in enumerate(silence_mask):
            if is_silent and not in_silence:
                silence_start = time_points[i]
                in_silence = True

            elif not is_silent and in_silence:
                silence_end = time_points[i]
                if silence_end - silence_start > 0.1:  # 至少 0.1 秒
                    regions.append(SilenceRegion(
                        start_time=silence_start,
                        end_time=silence_end,
                        duration=silence_end - silence_start
                    ))
                in_silence = False

        return regions
```

## 错误处理

### 错误代码

| 代码 | 描述 | 可重试 |
|------|------|--------|
| M002-001 | 视频文件损坏 | 否 |
| M002-002 | 不支持的编码格式 | 否 |
| M002-003 | FFmpeg 执行失败 | 是 |
| M002-004 | 音频提取失败 | 是 |
| M002-005 | 场景检测超时 | 是 |
| M002-006 | GPU 内存不足 | 是 |

### 降级策略

1. **GPU 不可用**: 切换到 CPU 处理
2. **场景检测失败**: 使用固定时间间隔切分
3. **音频分析失败**: 使用默认值

## 性能优化

1. **并行处理**: 场景检测和音频分析并行
2. **GPU 加速**: 使用 CUDA/OpenCL 加速
3. **降采样**: 对高分辨率视频先降采样
4. **缓存**: 缓存视频特征

## 测试要点

1. 各种视频格式测试
2. 不同分辨率测试
3. 各种帧率测试
4. 场景检测准确性
5. 音轨多语言处理
6. 性能测试（处理速度）

## 后续模块依赖

M02 的输出被以下模块使用：
- **M03**: 场景时间轴用于字幕对齐
- **M05**: 音频分析用于说话人识别
- **M07**: 对白区域用于对白处理
- **M10**: 音频分析用于混音
- **M11**: 场景信息用于视频组装
