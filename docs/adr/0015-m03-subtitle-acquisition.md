# ADR 0015: M03 字幕与对白获取模块设计

## 状态

设计中

## 上下文

M03 负责获取、解析、校正字幕，将字幕与视频时间轴对齐，为后续处理提供准确的对白时间轴。

## 核心职责

1. **字幕获取**: 从各种来源获取字幕（用户上传、网络下载）
2. **字幕解析**: 解析 SRT/ASS/VTT 等格式
3. **时间轴校正**: 校正字幕时间轴与视频的偏差
4. **对白切分**: 将字幕切分为独立的对话行
5. **对白时间轴构建**: 建立完整的对白时间轴

## 输入/输出

### 输入

```python
@dataclass
class M03Input:
    """M03 输入数据结构"""
    project_id: uuid.UUID
    job_id: uuid.UUID

    # 来自 M01 的字幕 Artifact
    subtitle_artifact_ids: List[uuid.UUID]

    # 来自 M02 的场景时间轴
    scene_timeline: SceneTimeline

    # 视频时长
    video_duration: float

    # 配置
    config: SubtitleConfig

@dataclass
class SubtitleConfig:
    """字幕配置"""
    # 对齐选项
    auto_align: bool = True          # 自动对齐时间轴
    sync_method: str = "waveform"   # waveform, speech, fixed

    # 字幕处理
    remove_formatting: bool = True   # 移除格式标记
    normalize_text: bool = True      # 文本规范化
    merge_short_lines: bool = False # 合并短行

    # 对白切分
    min_dialogue_length: float = 0.5  # 最短对白长度（秒）
    max_dialogue_gap: float = 2.0      # 最大对白间隔（秒）

    # 纠错
    fix_overlaps: bool = True       # 修复重叠字幕
    fix_rtl: bool = True            # 修复 RTL 语言
```

### 输出

```python
@dataclass
class M03Output:
    """M03 输出数据结构"""
    # 对白时间轴
    dialogue_timeline: DialogueTimeline

    # 字幕统计
    statistics: SubtitleStatistics

@dataclass
class DialogueTimeline:
    """对白时间轴"""
    dialogues: List[DialogueSegment]

    # 时间轴信息
    total_duration: float
    dialogue_count: int
    total_dialogue_duration: float

    # 覆盖率
    dialogue_coverage: float  # 对白占总时长比例

@dataclass
class DialogueSegment:
    """对白片段"""
    id: str
    index: int

    # 时间
    start_time: float
    end_time: float
    duration: float

    # 文本
    text: str
    original_text: str

    # 说话人（初步识别）
    speaker: Optional[str] = None
    speaker_confidence: float = 0.0

    # 语言
    language: str = "zh"
    text_direction: str = "ltr"  # ltr, rtl

    # 场景关联
    scene_id: Optional[str] = None
    shot_id: Optional[str] = None

@dataclass
class SubtitleStatistics:
    """字幕统计"""
    total_segments: int
    total_characters: int
    total_words: int
    average_characters_per_segment: float
    average_words_per_segment: float

    # 时间统计
    average_duration: float
    average_gap: float

    # 质量指标
    overlaps_fixed: int
    time_shifts: List[float]
```

## 模块架构

```
┌─────────────────────────────────────────────────────────┐
│                         M03                               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐               │
│  │  字幕解析器   │──────│  文本处理器   │               │
│  └──────────────┘      └──────────────┘               │
│         │                     │                             │
│         └──────────┬──────────┘                             │
│                    ▼                                       │
│         ┌────────────────────────┐                        │
│         │      时间轴校正器        │                        │
│         │   (对齐/同步/偏差修正)     │                        │
│         └────────────────────────┘                        │
│                    │                                       │
│                    ▼                                       │
│         ┌────────────────────────┐                        │
│         │      对白切分器          │                        │
│         │   (合并/切分/边界处理)     │                        │
│         └────────────────────────┘                        │
│                    │                                       │
│                    ▼                                       │
│         ┌────────────────────────┐                        │
│         │      时间轴构建器        │                        │
│         └────────────────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. 字幕解析器

```python
class UniversalSubtitleParser:
    """通用字幕解析器"""

    def __init__(self):
        self.parsers = {
            'srt': self._parse_srt,
            'ass': self._parse_ass,
            'ssa': self._parse_ass,
            'vtt': self._parse_vtt
        }

    async def parse(
        self,
        subtitle_artifact_id: uuid.UUID,
        artifact_registry: ArtifactRegistry
    ) -> List[RawSubtitle]:
        """解析字幕文件"""
        # 获取字幕内容
        subtitle_data = await self._download_subtitle(
            subtitle_artifact_id, artifact_registry
        )

        # 检测格式
        format_type = self._detect_format(subtitle_data)

        # 解析
        parser = self.parsers.get(format_type)
        if not parser:
            raise ValueError(f"Unsupported subtitle format: {format_type}")

        return parser(subtitle_data)

    def _detect_format(self, data: bytes) -> str:
        """检测字幕格式"""
        text = data.decode('utf-8', errors='ignore')

        if 'WebVTT' in text:
            return 'vtt'
        elif '[Script Info]' in text or '[V4 Styles]' in text:
            return 'ass'
        elif re.search(r'\d+\n\d{2}:\d{2}:\d{2}', text):
            return 'srt'
        else:
            return 'unknown'

    def _parse_srt(self, data: bytes) -> List[RawSubtitle]:
        """解析 SRT 字幕"""
        import pysrt

        subs = pysrt.from_string(data.decode('utf-8'))

        return [
            RawSubtitle(
                index=i + 1,
                start=sub.start.ordinal / 1000.0,
                end=sub.end.ordinal / 1000.0,
                text=sub.text
            )
            for i, sub in enumerate(subs)
        ]

    def _parse_ass(self, data: bytes) -> List[RawSubtitle]:
        """解析 ASS/SSA 字幕"""
        import subprocess

        # 使用 ffmpeg 转换为 SRT
        result = subprocess.run(
            ['ffmpeg', '-i', 'input.ass', '-f', 'srt', 'output.srt'],
            capture_output=True
        )

        # 然后用 SRT 解析
        return self._parse_srt(result.stdout)

    def _parse_vtt(self, data: bytes) -> List[RawSubtitle]:
        """解析 VTT 字幕"""
        import webvtt

        subs = webvtt.from_string(data.decode('utf-8'))

        return [
            RawSubtitle(
                index=i,
                start=sub.start_in_seconds,
                end=sub.end_in_seconds,
                text=sub.text
            )
            for i, sub in enumerate(subs)
        ]

@dataclass
class RawSubtitle:
    """原始字幕"""
    index: int
    start: float
    end: float
    text: str
```

### 2. 时间轴校正器

```python
class TimelineAligner:
    """时间轴校正器"""

    async def align(
        self,
        subtitles: List[RawSubtitle],
        video_duration: float,
        scene_timeline: SceneTimeline,
        config: SubtitleConfig
    ) -> List[RawSubtitle]:
        """对齐字幕时间轴"""
        if config.sync_method == "waveform":
            return await self._align_by_waveform(subtitles, video_duration)
        elif config.sync_method == "speech":
            return await self._align_by_speech(subtitles)
        elif config.sync_method == "fixed":
            return await self._align_by_fixed(subtitles, scene_timeline)
        else:
            return subtitles

    async def _align_by_waveform(
        self,
        subtitles: List[RawSubtitle],
        video_duration: float
    ) -> List[RawSubtitle]:
        """基于波形对齐"""
        # 使用 ffmpeg 提取音频波形
        # 计算字幕时间与实际语音的对应关系

        # 这里简化处理：检测全局偏移
        offset = await self._detect_global_offset(subtitles, video_duration)

        aligned = []
        for sub in subtitles:
            aligned.append(RawSubtitle(
                index=sub.index,
                start=max(0, sub.start + offset),
                end=min(video_duration, sub.end + offset),
                text=sub.text
            ))

        return aligned

    async def _detect_global_offset(
        self,
        subtitles: List[RawSubtitle],
        video_duration: float
    ) -> float:
        """检测全局时间偏移"""
        # 使用第一个字幕和最后一个字幕的位置
        # 假设正常情况下，字幕应该大致分布在视频中间 80%

        if not subtitles:
            return 0.0

        first_sub = subtitles[0]
        last_sub = subtitles[-1]

        expected_first = video_duration * 0.1  # 前 10%
        expected_last = video_duration * 0.9   # 后 10%

        # 计算平均偏移
        offset = (expected_first - first_sub.start + expected_last - last_sub.end) / 2

        # 限制偏移范围
        return max(-10.0, min(10.0, offset))  # ±10 秒

    async def _align_by_speech(
        self,
        subtitles: List[RawSubtitle]
    ) -> List[RawSubtitle]:
        """基于语音检测对齐"""
        # 使用 WhisperX 进行精确对齐
        # 这将调用 M02/M05 的音频分析能力

        # 简化实现：返回原始字幕
        return subtitles

    async def _align_by_fixed(
        self,
        subtitles: List[RawSubtitle],
        scene_timeline: SceneTimeline
    ) -> List[RawSubtitle]:
        """基于场景边界对齐"""
        # 将字幕映射到场景中
        aligned = []

        for sub in subtitles:
            # 找到所属场景
            for scene in scene_timeline.scenes:
                if scene.start_time <= sub.start <= scene.end_time:
                    # 调整到场景内相对位置
                    scene_progress = (sub.start - scene.start_time) / scene.duration
                    adjusted_start = scene.start_time + scene_progress * scene.duration
                    adjusted_end = scene.start_time + ((sub.end - sub.start) / scene.duration) * scene.duration

                    aligned.append(RawSubtitle(
                        index=sub.index,
                        start=adjusted_start,
                        end=adjusted_end,
                        text=sub.text
                    ))
                    break

        return aligned
```

### 3. 对白切分器

```python
class DialogueSegmenter:
    """对白切分器"""

    async def segment(
        self,
        subtitles: List[RawSubtitle],
        config: SubtitleConfig
    ) -> List[DialogueSegment]:
        """切分对白"""
        segments = []

        for i, sub in enumerate(subtitles):
            # 处理文本
            processed_text = self._process_text(sub.text, config)

            # 检测是否需要合并
            if i > 0 and self._should_merge(
                subtitles[i-1], sub, config
            ):
                # 合并到前一个片段
                segments[-1].text += " " + processed_text
                segments[-1].end_time = sub.end
                segments[-1].duration = segments[-1].end_time - segments[-1].start_time
                continue

            # 创建新片段
            segments.append(DialogueSegment(
                id=f"dialogue_{i}",
                index=i,
                start_time=sub.start,
                end_time=sub.end,
                duration=sub.end - sub.start,
                text=processed_text,
                original_text=sub.text,
                language="zh",  # 将在 M06 中识别
                text_direction="ltr"
            ))

        return segments

    def _process_text(self, text: str, config: SubtitleConfig) -> str:
        """处理文本"""
        # 移除格式标记
        if config.remove_formatting:
            text = self._remove_formatting(text)

        # 规范化文本
        if config.normalize_text:
            text = self._normalize_text(text)

        return text.strip()

    def _remove_formatting(self, text: str) -> str:
        """移除格式标记"""
        import re

        # 移除 ASS/SSA 格式
        text = re.sub(r'\{.*?\}', '', text)  # 移除 {} 标记
        text = re.sub(r'<.*?>', '', text)   # 移除 HTML 标签

        # 移除常见格式标记
        text = re.sub(r'\\[nN]', '', text)   # 移除换行符
        text = re.sub(r'\\[kK]', '', text)   # 移除颜色标记

        return text

    def _normalize_text(self, text: str) -> str:
        """规范化文本"""
        import re

        # 统一标点
        text = text.replace('，', '，').replace('。', '。')
        text = text.replace('?', '？').replace('!', '！')

        # 移除多余空格
        text = re.sub(r'\s+', ' ', text)

        # 移除特殊符号
        text = re.sub(r'[​-‍﻿]', '', text)

        return text.strip()

    def _should_merge(
        self,
        prev: RawSubtitle,
        curr: RawSubtitle,
        config: SubtitleConfig
    ) -> bool:
        """判断是否应该合并"""
        # 检查间隔
        gap = curr.start - prev.end

        if gap > config.max_dialogue_gap:
            return False

        # 检查长度
        prev_duration = prev.end - prev.start

        if prev_duration < config.min_dialogue_length:
            return True

        return config.merge_short_lines
```

### 4. 时间轴构建器

```python
class TimelineBuilder:
    """时间轴构建器"""

    async def build(
        self,
        segments: List[DialogueSegment],
        video_duration: float,
        scene_timeline: SceneTimeline
    ) -> DialogueTimeline:
        """构建对白时间轴"""
        # 设置关联
        for seg in segments:
            # 关联场景
            for scene in scene_timeline.scenes:
                if scene.start_time <= seg.start_time <= scene.end_time:
                    seg.scene_id = scene.id
                    break

        # 计算统计信息
        total_dialogue_duration = sum(s.duration for s in segments)
        dialogue_coverage = total_dialogue_duration / video_duration if video_duration > 0 else 0

        return DialogueTimeline(
            dialogues=segments,
            total_duration=video_duration,
            dialogue_count=len(segments),
            total_dialogue_duration=total_dialogue_duration,
            dialogue_coverage=dialogue_coverage
        )
```

## 错误处理

### 错误代码

| 代码 | 描述 | 可重试 |
|------|------|--------|
| M003-001 | 字幕格式不支持 | 否 |
| M003-002 | 字幕编码错误 | 否 |
| M003-003 | 字幕时间轴无效 | 是 |
| M003-004 | 时间轴对齐失败 | 是 |
| M003-005 | 字幕与视频不匹配 | 否 |

### 降级策略

1. **格式不支持**: 尝试转换为 SRT
2. **对齐失败**: 使用原始时间轴
3. **编码错误**: 尝试多种编码

## 测试要点

1. 各种字幕格式测试
2. 各种编码测试
3. 时间轴偏移处理
4. 文本处理准确性
5. 场景关联准确性
6. 边界情况处理

## 后续模块依赖

M03 的输出被以下模块使用：
- **M04**: 对白文本用于人物识别
- **M06**: 对白时间轴用于说话人映射
- **M07**: 对白文本用于智能处理
- **M08**: 对白用于韵律规划
- **M09**: 对白用于语音合成
