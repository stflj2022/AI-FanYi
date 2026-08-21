# Wayfinder Map: 影视AI配音平台 MVP

## 总体地图

```
MAP: 影视AI配音平台 MVP 实现
│
├── LAYER0: Layer 0 编排层 (Orchestrator)
│   ├── 项目管理 (Project/Job/Workflow)
│   ├── Artifact Registry
│   ├── 资源调度 (GPU/CPU)
│   ├── Worker 管理
│   ├── 断点恢复
│   └── Web UI
│
├── M01: 项目与媒体输入
│   ├── 视频上传和验证
│   ├── 字幕解析 (SRT/ASS/VTT)
│   ├── 元数据获取 (TMDB/IMDb)
│   └── Media Manifest 生成
│
├── M02: 项目研究与身份解析
│   ├── 媒体分析 (编码/分辨率/FPS)
│   ├── 音频轨分析
│   ├── 场景检测
│   ├── 镜头检测
│   └── 时间轴分析
│
├── M03: 字幕与对白获取
│   ├── 字幕校正
│   ├── 时间轴校正
│   ├── 对白切分
│   └── Dialogue Timeline 生成
│
├── M04: 人物数据库构建
│   ├── Character Schema 设计
│   ├── 人物信息获取 (TMDB)
│   ├── 说话人聚类
│   ├── 人物关系构建
│   └── Character DB 实现
│
├── M05: 音频与场景分析
│   ├── ASR (Whisper)
│   ├── Speaker Diarization
│   ├── 音频特征提取
│   └── 音频预处理
│
├── M06: 说话人→人物→音色身份
│   ├── Speaker → Character 映射
│   ├── Voice Profile 创建
│   ├── 音色匹配算法
│   └── Voice DB 构建
│
├── M07: 字幕/对白智能
│   ├── 对白清洗
│   ├── 情绪分析
│   ├── 断句优化
│   └── 口语化处理
│
├── M08: 韵律与表演规划
│   ├── 语速规划
│   ├── 停顿规划
│   ├── 情绪标签
│   └── TTS 参数生成
│
├── M09: 语音合成
│   ├── TTS 集成 (CosyVoice)
│   ├── 音色克隆
│   ├── 情绪控制
│   └── 批量生成
│
├── M10: 对白音频处理与场景混音
│   ├── 音频对齐
│   ├── 语速调整
│   ├── 音量归一化
│   └── 背景音混音
│
├── M11: 视频组装与最终编码
│   ├── 音视频同步
│   ├── 字幕嵌入
│   └── 最终编码
│
├── M12: 项目质检与人工审查
│   ├── 自动质检规则
│   ├── QA 报告生成
│   └── 人工审查界面
│
├── M13: 批量/季集流水线
│   ├── 批量任务调度
│   ├── 季集管理
│   └── 跨集数据共享
│
└── M14: 项目归档与可复现性
    ├── 完整归档
    ├── 版本记录
    └── 可复现性保证
```

## 实现优先级

### Phase 1: 基础设施 (必需)
1. **LAYER0**: 核心编排、Artifact Registry
2. **M01**: 项目输入，系统入口
3. **M02**: 基础媒体分析

### Phase 2: 核心数据 (必需)
4. **M04**: 人物数据库
5. **M05**: 音频分析
6. **M06**: Speaker-Character 映射

### Phase 3: 核心处理 (核心功能)
7. **M03**: 字幕处理
8. **M07**: 对白智能
9. **M08**: 韵律规划
10. **M09**: TTS 合成

### Phase 4: 输出和质量 (交付)
11. **M10**: 音频处理
12. **M11**: 视频组装
13. **M12**: 质检

### Phase 5: 高级功能 (增强)
14. **M13**: 批量/季集
15. **M14**: 归档

## 技术依赖

```
Layer 0 (FastAPI + PostgreSQL + Redis)
    ├── M01 (FFmpeg + MediaInfo)
    ├── M02 (FFmpeg + PyAV + OpenCV)
    ├── M03 (WhisperX + 字幕工具)
    ├── M04 (Speaker Diarization + TMDB API)
    ├── M05 (Whisper + Pyannote)
    ├── M06 (Speaker Embedding + 算法)
    ├── M07 (Qwen LLM)
    ├── M08 (Qwen LLM)
    ├── M09 (CosyVoice/F5-TTS)
    ├── M10 (FFmpeg + SoX + DSP)
    ├── M11 (FFmpeg)
    ├── M12 (规则引擎)
    ├── M13 (调度器)
    └── M14 (存储 + 版本控制)
```

## GitHub 标签

用于 GitHub Issues 标签：
- `wayfinder:map` - 总体地图
- `wayfinder:feature` - 功能模块
- `wayfinder:tech-debt` - 技术债务
- `layer:0` - Layer 0 相关
- `module:m01` - `module:m14` - 各模块相关
- `phase:1` - `phase:5` - 实现阶段
