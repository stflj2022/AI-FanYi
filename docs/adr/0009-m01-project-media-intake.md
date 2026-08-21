# ADR 0009: M01 项目与媒体输入模块设计

## 状态

设计中

## 上下文

M01 是整个平台的入口模块，负责接收用户的输入（视频、字幕、基本信息），创建项目，并获取元数据。

## 核心职责

1. **项目创建**: 接收用户输入，创建 Project
2. **媒体上传**: 接收视频和字幕文件
3. **媒体验证**: 验证媒体格式、完整性
4. **元数据获取**: 从 TMDB/IMDb 获取剧集信息
5. **字幕解析**: 解析 SRT/ASS/VTT 字幕
6. **Manifest 生成**: 生成 Media Manifest

## 输入/输出

### 输入

```python
@dataclass
class M01Input:
    """M01 输入数据结构"""
    # 基本信息
    project_name: str
    description: Optional[str]

    # 媒体类型
    media_type: MediaType  # movie, tv_series, documentary, anime

    # 视频文件
    video_file: UploadFile
    video_info: VideoInfo

    # 字幕文件（可选）
    subtitle_files: List[UploadFile] = None

    # 元数据（可选，如果不提供则自动获取）
    title: Optional[str] = None
    title_en: Optional[str] = None
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None

    # 语言
    source_language: str = "en"
    target_language: str = "zh-CN"

    # 外部 ID（可选）
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None

@dataclass
class VideoInfo:
    """视频信息"""
    format: str              # mp4, mkv, avi
    codec: str               # h264, h265, hevc
    width: int               # 像素
    height: int              # 像素
    fps: float               # 帧率
    duration_seconds: float  # 时长
    size_bytes: int          # 大小
    bitrate: int             # 比特率
    audio_tracks: List[AudioTrack]
    subtitle_tracks: List[SubtitleTrack]

@dataclass
class AudioTrack:
    """音轨信息"""
    index: int
    codec: str
    language: str
    channels: int            # 1=mono, 2=stereo, 6=5.1
    sample_rate: int
    bitrate: int

@dataclass
class SubtitleTrack:
    """字幕轨道信息"""
    index: int
    language: str
    format: str              # srt, ass, vtt
    external: bool           # 是否外挂字幕
```

### 输出

```python
@dataclass
class M01Output:
    """M01 输出数据结构"""
    # 项目信息
    project_id: uuid.UUID
    status: str = "intake"

    # Artifact 列表
    artifacts: List[ArtifactRef]

    # 元数据
    metadata: ProjectMetadata

    # Media Manifest
    media_manifest: MediaManifest

@dataclass
class ProjectMetadata:
    """项目元数据"""
    title: str
    title_en: str
    title_original: Optional[str]
    overview: Optional[str]
    genres: List[str]
    runtime: Optional[int]
    release_date: Optional[str]
    vote_average: Optional[float]
    vote_count: Optional[int]
    poster_path: Optional[str]
    backdrop_path: Optional[str]

    # 剧集信息
    seasons: Optional[List[SeasonInfo]]
    episodes: Optional[List[EpisodeInfo]]

    # 演职人员
    cast: List[CastInfo]
    crew: List[CrewInfo]

@dataclass
class MediaManifest:
    """媒体清单"""
    project_id: uuid.UUID
    source_video: VideoSource
    source_subtitles: List[SubtitleSource]

    # 时间轴信息
    total_duration: float
    framerate: float

    # 章节标记（如果存在）
    chapters: List[Chapter] = None

@dataclass
class VideoSource:
    """视频源"""
    artifact_id: uuid.UUID
    filename: str
    format: str
    codec: str
    resolution: str
    duration: float
    size_bytes: int
    bitrate: int
    checksum: str
```

## 模块架构

```
┌─────────────────────────────────────────────────────────┐
│                        M01                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐               │
│  │  输入验证器   │──────│  媒体处理器  │               │
│  └──────────────┘      └──────────────┘               │
│         │                      │                          │
│         ▼                      ▼                          │
│  ┌──────────────┐      ┌──────────────┐               │
│  │ 元数据获取器 │      │  字幕解析器  │               │
│  └──────────────┘      └──────────────┘               │
│         │                      │                          │
│         └──────────┬───────────┘                          │
│                    ▼                                       │
│           ┌──────────────┐                                │
│           │ Manifest 构建│                                │
│           └──────────────┘                                │
│                    │                                       │
│                    ▼                                       │
│           ┌──────────────┐                                │
│           │ Artifact 创建│                                │
│           └──────────────┘                                │
└─────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. 输入验证器

```python
class InputValidator:
    """输入验证器"""

    def __init__(self):
        self.allowed_video_formats = ['mp4', 'mkv', 'avi', 'mov', 'wmv']
        self.allowed_subtitle_formats = ['srt', 'ass', 'ssa', 'vtt']
        self.max_video_size = 10 * 1024 * 1024 * 1024  # 10GB
        self.max_subtitle_size = 10 * 1024 * 1024  # 10MB

    async def validate_input(self, input_data: M01Input) -> ValidationResult:
        """验证输入数据"""
        errors = []
        warnings = []

        # 验证视频格式
        video_ext = input_data.video_file.filename.split('.')[-1].lower()
        if video_ext not in self.allowed_video_formats:
            errors.append(f"Unsupported video format: {video_ext}")

        # 验证视频大小
        video_size = len(await input_data.video_file.read())
        await input_data.video_file.seek(0)

        if video_size > self.max_video_size:
            errors.append(f"Video too large: {video_size} bytes")

        if video_size == 0:
            errors.append("Video file is empty")

        # 验证字幕
        if input_data.subtitle_files:
            for sub_file in input_data.subtitle_files:
                sub_ext = sub_file.filename.split('.')[-1].lower()
                if sub_ext not in self.allowed_subtitle_formats:
                    warnings.append(f"Subtitle format not supported: {sub_ext}")

                sub_size = len(await sub_file.read())
                await sub_file.seek(0)

                if sub_size > self.max_subtitle_size:
                    warnings.append(f"Subtitle too large: {sub_size} bytes")

        # 验证必填字段
        if not input_data.project_name:
            errors.append("Project name is required")

        if not input_data.media_type:
            errors.append("Media type is required")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    async def validate_video_integrity(self, video_path: str) -> bool:
        """验证视频完整性"""
        try:
            # 使用 FFmpeg 验证
            result = subprocess.run(
                ['ffmpeg', '-v', 'error', '-i', video_path, '-f', 'null', '-'],
                capture_output=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"Video validation failed: {result.stderr.decode()}")
                return False

            return True

        except subprocess.TimeoutExpired:
            logger.error("Video validation timeout")
            return False
        except Exception as e:
            logger.error(f"Video validation error: {e}")
            return False
```

### 2. 媒体处理器

```python
class MediaProcessor:
    """媒体处理器"""

    def __init__(self, artifact_registry: ArtifactRegistry):
        self.artifact_registry = artifact_registry

    async def process_video(
        self,
        video_file: UploadFile,
        project_id: uuid.UUID,
        job_id: uuid.UUID
    ) -> VideoSource:
        """处理视频文件

        1. 上传到 Artifact Registry
        2. 提取视频信息
        3. 生成校验和
        """
        # 创建 Artifact
        metadata = ArtifactMetadata(
            name=video_file.filename,
            type=ArtifactType.VIDEO,
            project_id=project_id,
            job_id=job_id,
            module_id="M01",
            mime_type=self._get_mime_type(video_file.filename)
        )

        artifact_ref = await self.artifact_registry.create(metadata)

        # 上传文件
        await self.artifact_registry.upload(
            artifact_ref.id,
            video_file.file
        )

        # 提取视频信息
        video_info = await self._extract_video_info(video_file)

        # 生成校验和
        checksum = await self._calculate_checksum(video_file)

        return VideoSource(
            artifact_id=artifact_ref.id,
            filename=video_file.filename,
            format=video_info.format,
            codec=video_info.codec,
            resolution=f"{video_info.width}x{video_info.height}",
            duration=video_info.duration_seconds,
            size_bytes=video_info.size_bytes,
            bitrate=video_info.bitrate,
            checksum=checksum
        )

    async def _extract_video_info(self, video_file: UploadFile) -> VideoInfo:
        """提取视频信息"""
        import cv2
        import ffmpeg

        # 临时保存文件
        temp_path = f"/tmp/{uuid.uuid4()}"
        with open(temp_path, 'wb') as f:
            f.write(await video_file.read())

        try:
            # 使用 FFmpeg 提取信息
            probe = ffmpeg.probe(temp_path)

            video_stream = None
            audio_streams = []
            subtitle_streams = []

            for stream in probe['streams']:
                if stream['codec_type'] == 'video':
                    video_stream = stream
                elif stream['codec_type'] == 'audio':
                    audio_streams.append(stream)
                elif stream['codec_type'] == 'subtitle':
                    subtitle_streams.append(stream)

            # 解析音频轨道
            audio_tracks = []
            for i, stream in enumerate(audio_streams):
                audio_tracks.append(AudioTrack(
                    index=i,
                    codec=stream.get('codec_name', 'unknown'),
                    language=stream.get('tags', {}).get('language', 'und'),
                    channels=int(stream.get('channels', 2)),
                    sample_rate=int(stream.get('sample_rate', 48000)),
                    bitrate=int(stream.get('bit_rate', 0))
                ))

            # 解析字幕轨道
            subtitle_tracks = []
            for i, stream in enumerate(subtitle_streams):
                subtitle_tracks.append(SubtitleTrack(
                    index=i,
                    language=stream.get('tags', {}).get('language', 'und'),
                    format=stream.get('codec_name', 'unknown'),
                    external=False
                ))

            return VideoInfo(
                format=probe['format'].get('format_name', 'unknown'),
                codec=video_stream.get('codec_name', 'unknown') if video_stream else 'unknown',
                width=int(video_stream.get('width', 0)) if video_stream else 0,
                height=int(video_stream.get('height', 0)) if video_stream else 0,
                fps=eval(video_stream.get('r_frame_rate', '0/1')) if video_stream else 0.0,
                duration_seconds=float(probe['format'].get('duration', 0)),
                size_bytes=int(probe['format'].get('size', 0)),
                bitrate=int(probe['format'].get('bit_rate', 0)),
                audio_tracks=audio_tracks,
                subtitle_tracks=subtitle_tracks
            )

        finally:
            os.remove(temp_path)

    def _get_mime_type(self, filename: str) -> str:
        """获取 MIME 类型"""
        ext = filename.split('.')[-1].lower()
        mime_types = {
            'mp4': 'video/mp4',
            'mkv': 'video/x-matroska',
            'avi': 'video/x-msvideo',
            'mov': 'video/quicktime',
            'wmv': 'video/x-ms-wmv'
        }
        return mime_types.get(ext, 'video/octet-stream')

    async def _calculate_checksum(self, file: UploadFile) -> str:
        """计算文件校验和"""
        import hashlib
        sha256 = hashlib.sha256()

        await file.seek(0)
        while chunk := await file.read(8192):
            sha256.update(chunk)

        return f"sha256:{sha256.hexdigest()}"
```

### 3. 元数据获取器

```python
class MetadataFetcher:
    """元数据获取器"""

    def __init__(self, tmdb_api_key: str):
        self.tmdb_api_key = tmdb_api_key
        self.tmdb_base_url = "https://api.themoviedb.org/3"

    async def fetch_metadata(
        self,
        input_data: M01Input
    ) -> ProjectMetadata:
        """获取项目元数据"""
        # 如果已提供 TMDB ID，直接获取
        if input_data.tmdb_id:
            return await self._fetch_by_tmdb_id(input_data.tmdb_id)

        # 如果提供了标题，搜索
        if input_data.title_en:
            return await self._search_and_fetch(
                input_data.title_en,
                input_data.media_type,
                input_data.year
            )

        # 尝试从视频文件名推断
        inferred_title = self._infer_title_from_filename(input_data.video_file.filename)
        if inferred_title:
            return await self._search_and_fetch(
                inferred_title,
                input_data.media_type,
                input_data.year
            )

        # 无法获取元数据，返回基础信息
        return ProjectMetadata(
            title=input_data.project_name,
            title_en=input_data.title_en or input_data.project_name,
            title_original=None,
            overview=None,
            genres=[],
            runtime=None,
            release_date=None,
            vote_average=None,
            vote_count=None,
            poster_path=None,
            backdrop_path=None,
            seasons=None,
            episodes=None,
            cast=[],
            crew=[]
        )

    async def _fetch_by_tmdb_id(self, tmdb_id: int) -> ProjectMetadata:
        """通过 TMDB ID 获取"""
        async with httpx.AsyncClient() as client:
            # 获取基本信息
            response = await client.get(
                f"{self.tmdb_base_url}/tv/{tmdb_id}",
                params={"api_key": self.tmdb_api_key}
            )
            data = response.json()

            # 获取演职人员
            credits_response = await client.get(
                f"{self.tmdb_base_url}/tv/{tmdb_id}/credits",
                params={"api_key": self.tmdb_api_key}
            )
            credits = credits_response.json()

            return self._parse_tmdb_data(data, credits)

    async def _search_and_fetch(
        self,
        title: str,
        media_type: MediaType,
        year: Optional[int] = None
    ) -> ProjectMetadata:
        """搜索并获取元数据"""
        async with httpx.AsyncClient() as client:
            # 搜索
            search_params = {
                "api_key": self.tmdb_api_key,
                "query": title
            }

            if media_type == MediaType.TV_SERIES:
                search_params["type"] = "tv"
            elif media_type == MediaType.MOVIE:
                search_params["type"] = "movie"

            if year:
                search_params["year"] = year

            search_response = await client.get(
                f"{self.tmdb_base_url}/search/{search_params['type']}",
                params=search_params
            )

            search_data = search_response.json()

            if not search_data.get("results"):
                raise ValueError(f"No results found for: {title}")

            # 取第一个结果
            first_result = search_data["results"][0]
            tmdb_id = first_result["id"]

            # 获取详细信息
            return await self._fetch_by_tmdb_id(tmdb_id)

    def _parse_tmdb_data(self, data: Dict, credits: Dict) -> ProjectMetadata:
        """解析 TMDB 数据"""
        # 解析季数信息
        seasons = []
        if "seasons" in data:
            for season_data in data["seasons"]:
                seasons.append(SeasonInfo(
                    season_number=season_data["season_number"],
                    episode_count=season_data["episode_count"],
                    name=season_data["name"],
                    overview=season_data.get("overview"),
                    poster_path=season_data.get("poster_path")
                ))

        # 解析演员
        cast = []
        for cast_data in credits.get("cast", [])[:20]:  # 前20个主要演员
            cast.append(CastInfo(
                id=cast_data["id"],
                name=cast_data["name"],
                character=cast_data.get("character"),
                order=cast_data["order"],
                profile_path=cast_data.get("profile_path")
            ))

        # 解析职员
        crew = []
        for crew_data in credits.get("crew", []):
            crew.append(CrewInfo(
                id=crew_data["id"],
                name=crew_data["name"],
                department=crew_data.get("department"),
                job=crew_data.get("job"),
                profile_path=crew_data.get("profile_path")
            ))

        return ProjectMetadata(
            title=data.get("name", ""),
            title_en=data.get("name", ""),
            title_original=data.get("original_name"),
            overview=data.get("overview"),
            genres=[g["name"] for g in data.get("genres", [])],
            runtime=data.get("episode_run_time", [None])[0],
            release_date=data.get("first_air_date"),
            vote_average=data.get("vote_average"),
            vote_count=data.get("vote_count"),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            seasons=seasons if seasons else None,
            episodes=None,
            cast=cast,
            crew=crew
        )

    def _infer_title_from_filename(self, filename: str) -> Optional[str]:
        """从文件名推断标题"""
        # 移除扩展名
        name = os.path.splitext(filename)[0]

        # 常见模式：
        # Show.Name.S01E01.tag
        # Show.Name_-_s01e01_-_tag
        # Show.Name.1x01.tag

        # 移除季集信息
        import re
        name = re.sub(r'[.\s_-]*[sS]\d+[eE]\d+.*', '', name)
        name = re.sub(r'[.\s_-]*\d+x\d+.*', '', name)
        name = re.sub(r'[.\s_-]*\d{3,4}p.*', '', name)

        # 替换分隔符为空格
        name = re.sub(r'[._-]', ' ', name)

        return name.strip() if name else None
```

### 4. 字幕解析器

```python
class SubtitleParser:
    """字幕解析器"""

    def __init__(self, artifact_registry: ArtifactRegistry):
        self.artifact_registry = artifact_registry

    async def parse_subtitle(
        self,
        subtitle_file: UploadFile,
        project_id: uuid.UUID,
        job_id: uuid.UUID
    ) -> SubtitleSource:
        """解析字幕文件"""
        # 读取文件内容
        content = await subtitle_file.read()

        # 根据格式解析
        ext = subtitle_file.filename.split('.')[-1].lower()

        if ext == 'srt':
            subtitles = self._parse_srt(content)
        elif ext in ['ass', 'ssa']:
            subtitles = self._parse_ass(content)
        elif ext == 'vtt':
            subtitles = self._parse_vtt(content)
        else:
            raise ValueError(f"Unsupported subtitle format: {ext}")

        # 保存为 Artifact
        metadata = ArtifactMetadata(
            name=subtitle_file.filename,
            type=ArtifactType.SUBTITLE,
            project_id=project_id,
            job_id=job_id,
            module_id="M01",
            mime_type=f"text/{ext}"
        )

        artifact_ref = await self.artifact_registry.create(metadata)

        # 保存解析后的字幕
        subtitle_data = {
            "format": ext,
            "language": self._detect_language(content),
            "subtitles": [
                {
                    "index": i,
                    "start": sub.start,
                    "end": sub.end,
                    "text": sub.text
                }
                for i, sub in enumerate(subtitles)
            ]
        }

        # 上传到 Artifact Registry
        import json
        await self.artifact_registry.upload(
            artifact_ref.id,
            json.dumps(subtitle_data).encode()
        )

        return SubtitleSource(
            artifact_id=artifact_ref.id,
            filename=subtitle_file.filename,
            format=ext,
            language=self._detect_language(content),
            subtitle_count=len(subtitles)
        )

    def _parse_srt(self, content: bytes) -> List[Subtitle]:
        """解析 SRT 字幕"""
        import pysrt

        subtitles = []
        srt_data = pysrt.from_string(content.decode('utf-8'))

        for sub in srt_data:
            subtitles.append(Subtitle(
                start=sub.start.ordinal / 1000.0,  # 转换为秒
                end=sub.end.ordinal / 1000.0,
                text=sub.text
            ))

        return subtitles

    def _parse_ass(self, content: bytes) -> List[Subtitle]:
        """解析 ASS/SSA 字幕"""
        # 简化处理，实际需要更复杂的解析
        import re

        pattern = r'Dialogue: \d+,(\d+:\d+:\d+\.\d+),(\d+:\d+:\d+\.\d+),[^,]*,[^,]*,(.*)'

        subtitles = []
        for match in re.finditer(pattern, content.decode('utf-8')):
            start_time = self._parse_ass_time(match.group(1))
            end_time = self._parse_ass_time(match.group(2))
            text = match.group(3).replace(r'\N', '\n')

            subtitles.append(Subtitle(
                start=start_time,
                end=end_time,
                text=text
            ))

        return subtitles

    def _parse_vtt(self, content: bytes) -> List[Subtitle]:
        """解析 VTT 字幕"""
        # 类似 SRT 格式
        import webvtt

        subtitles = []
        vtt_data = webvtt.from_string(content.decode('utf-8'))

        for sub in vtt_data:
            subtitles.append(Subtitle(
                start=sub.start_in_seconds,
                end=sub.end_in_seconds,
                text=sub.text
            ))

        return subtitles

    def _parse_ass_time(self, time_str: str) -> float:
        """解析 ASS 时间格式 (h:mm:ss.cs)"""
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)

    def _detect_language(self, content: bytes) -> str:
        """检测字幕语言"""
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            return 'unknown'

        # 简单的字符集检测
        chinese_chars = len([c for c in text if '一' <= c <= '鿿'])
        total_chars = len([c for c in text if c.isalpha()])

        if total_chars == 0:
            return 'unknown'

        chinese_ratio = chinese_chars / total_chars

        if chinese_ratio > 0.3:
            return 'zh'
        else:
            return 'en'
```

### 5. Manifest 构建

```python
class ManifestBuilder:
    """Media Manifest 构建器"""

    def build(
        self,
        project_id: uuid.UUID,
        video_source: VideoSource,
        subtitle_sources: List[SubtitleSource],
        video_info: VideoInfo
    ) -> MediaManifest:
        """构建 Media Manifest"""
        # 计算总时长
        total_duration = video_info.duration_seconds

        # 检测章节（如果存在）
        chapters = self._detect_chapters(video_source)

        return MediaManifest(
            project_id=project_id,
            source_video=video_source,
            source_subtitles=subtitle_sources,
            total_duration=total_duration,
            framerate=video_info.fps,
            chapters=chapters
        )

    def _detect_chapters(self, video_source: VideoSource) -> List[Chapter]:
        """检测视频章节"""
        # 可以从 FFmpeg 章节信息中提取
        # 或者根据黑屏/场景变化自动检测
        # 这里返回空列表，实际检测在 M02 进行
        return []
```

## 错误处理

### 错误代码

| 代码 | 描述 | 可重试 |
|------|------|--------|
| M001-001 | 视频文件格式不支持 | 否 |
| M001-002 | 视频文件损坏 | 否 |
| M001-003 | 字幕文件格式不支持 | 否 |
| M001-004 | 字幕文件损坏 | 否 |
| M001-005 | 元数据获取失败 | 是 |
| M001-006 | 网络超时 | 是 |
| M001-007 | 存储空间不足 | 否 |

### 降级策略

1. **元数据获取失败**: 使用用户提供的基础信息
2. **字幕解析失败**: 继续处理，记录警告
3. **章节检测失败**: 返回空章节列表

## 性能优化

1. **并发处理**: 视频上传和元数据获取并发执行
2. **流式处理**: 大文件流式上传
3. **缓存**: TMDB 查询结果缓存

## 测试要点

1. 各种视频格式测试
2. 各种字幕格式测试
3. 损坏文件处理测试
4. 大文件处理测试
5. 元数据获取失败测试
6. 并发上传测试

## 后续模块依赖

M01 的输出被以下模块使用：
- **M02**: Media Manifest 和源视频
- **M03**: 字幕 Artifact
- **M04**: 项目元数据
- **M13**: 季集信息
