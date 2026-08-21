# Module 01: Project & Media Intake - 使用指南

## 概述

Module 01 是 FilmDub AI 的第一个模块，负责将用户提供的音视频文件转换为标准化、可验证的项目资产。

**定义**: Project & Media Intake 是 FilmDub AI 的不可变导入层。它将用户提供的音视频文件转换为经过验证、哈希、版本化的 Project/Episode/Media 资产和机器可读的清单，不执行任何 AI 推理或修改源媒体。

## 功能特性

- ✅ 文件上传和完整性检查（SHA-256）
- ✅ FFprobe 媒体分析
- ✅ 视频/音频/字幕流提取
- ✅ Project/Episode/Media ID 生成
- ✅ SQLite 数据库初始化
- ✅ 任务系统与状态跟踪
- ✅ 原子化文件写入
- ✅ 幂等性设计（重复文件检测）

## 目录结构

```
filmdub/
├── apps/
│   └── api/              # FastAPI 后端
├── core/
│   ├── config/           # 配置管理
│   ├── database/         # 数据库连接
│   ├── models/           # SQLAlchemy 模型
│   ├── schemas/          # Pydantic schemas
│   └── storage/          # 文件存储管理
├── workers/
│   └── media_intake/     # Module 01 Worker
├── tests/                # 测试套件
├── docker/               # Docker 配置
├── scripts/              # 启动脚本
└── projects/             # 项目数据存储
```

## 安装

### 1. 系统依赖

```bash
# 安装 FFmpeg
sudo apt update
sudo apt install -y ffmpeg python3.13-venv python3-full
```

### 2. Python 虚拟环境

```bash
cd /media/w/4b5b3535-4600-43ba-9b4e-71a83d1d6e43/AI-FanYi/filmdub
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. 配置

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置（可选，使用默认值即可）
nano .env
```

## 使用方法

### 命令行界面 (CLI)

#### 创建项目

```bash
source venv/bin/activate
python -m cli project create --title "绝命毒师" --target-language zh-CN
```

输出示例：
```
✓ Project created successfully!
  Project ID: proj_abc123def456
  Title: 绝命毒师
  Target Language: zh-CN
  Status: CREATED
```

#### 列出所有项目

```bash
python -m cli project list
```

#### 查看项目信息

```bash
python -m cli project info proj_abc123def456
```

#### 导入媒体文件

```bash
python -m cli media import proj_abc123def456 /path/to/Breaking.Bad.S01E01.mkv
```

输出示例：
```
✓ Media imported successfully!
  Job ID: job_xyz789
  Episode ID: ep_123abc456
  Media ID: med_def789ghi

  File: Breaking.Bad.S01E01.mkv
  Size: 3.42 GB
  Duration: 3612.5 seconds
  Container: matroska,webm
  SHA256: 8f3b7c9a1d2e3f4a5b6c7d8e9f0a1b2c...
```

#### 检查媒体详情

```bash
python -m cli media inspect proj_abc123def456 med_def789ghi
```

#### 查看任务状态

```bash
python -m cli job status proj_abc123def456 job_xyz789
```

### API 接口

#### 启动 API 服务器

```bash
# 方式 1: 使用脚本
./scripts/start_api.sh

# 方式 2: 直接运行
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

# 方式 3: 开发模式（自动重载）
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### API 端点

**健康检查**
```bash
curl http://localhost:8000/health
```

**创建项目**
```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "title": "绝命毒师",
    "target_language": "zh-CN"
  }'
```

**上传媒体**
```bash
curl -X POST http://localhost:8000/api/projects/proj_abc123def456/media \
  -F "file=@/path/to/video.mkv"
```

**获取项目信息**
```bash
curl http://localhost:8000/api/projects/proj_abc123def456
```

### Docker 部署

```bash
cd /media/w/4b5b3535-4600-43ba-9b4e-71a83d1d6e43/AI-FanYi/filmdub/docker
docker-compose up -d
```

## 项目结构说明

### 项目目录结构

创建项目后，会生成以下目录结构：

```
projects/
└── proj_abc123def456/
    ├── project.json              # 项目清单
    ├── database.sqlite           # SQLite 数据库
    ├── media/
    │   └── med_def789ghi/
    │       └── original.mkv      # 原始媒体文件（不可变）
    ├── manifests/
    │   ├── media.json            # 媒体清单
    │   └── project.json          # 项目清单副本
    ├── logs/
    │   └── intake.jsonl          # 处理日志
    └── jobs/
        └── job_xyz789.json       # 任务记录
```

### 数据库表结构

- **projects**: 项目信息
- **episodes**: 剧集信息
- **media_assets**: 媒体资产
- **media_streams**: 媒体流（视频/音频/字幕）
- **subtitle_assets**: 字幕资产
- **jobs**: 任务记录
- **job_events**: 任务事件日志

## 媒体清单 (Media Manifest) 示例

```json
{
  "schema_version": "1.0",
  "media_id": "med_def789ghi",
  "filename": "Breaking.Bad.S01E01.1080p.WEB-DL.mkv",
  "sha256": "8f3b7c9a1d2e3f4a5b6c7d8e9f0a1b2c...",
  "container": {
    "format": "matroska,webm",
    "format_long": "Matroska / WebM",
    "duration": 3612.45,
    "size_bytes": 3678912345,
    "bit_rate": 8142032
  },
  "video": {
    "index": 0,
    "codec": "h264",
    "codec_long": "H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
    "width": 1920,
    "height": 1080,
    "fps": 23.976,
    "duration": 3612.45,
    "bit_rate": 7500000,
    "pixel_format": "yuv420p",
    "is_default": true
  },
  "audio": [
    {
      "index": 1,
      "codec": "ac3",
      "codec_long": "ATSC A/52A (AC-3)",
      "language": "eng",
      "title": "English 5.1",
      "channels": 6,
      "channel_layout": "5.1",
      "sample_rate": 48000,
      "bit_rate": 640000,
      "duration": 3612.45,
      "is_default": true,
      "is_forced": false
    }
  ],
  "subtitles": [
    {
      "index": 2,
      "codec": "subrip",
      "codec_long": "SubRip subtitle",
      "language": "eng",
      "title": "English",
      "is_default": false,
      "is_forced": false
    },
    {
      "index": 3,
      "codec": "subrip",
      "codec_long": "SubRip subtitle",
      "language": "chi",
      "title": "Chinese Simplified",
      "is_default": false,
      "is_forced": false
    }
  ],
  "chapters": []
}
```

## 验收标准

Module 01 完成后，必须满足以下条件：

- [x] 原始文件安全存储（不可变）
- [x] SHA-256 哈希计算完成
- [x] FFprobe 分析成功
- [x] 至少包含一个视频流
- [x] 至少包含一个音频流
- [x] duration 有效
- [x] media.json 生成完成
- [x] project.json 生成完成
- [x] SQLite 数据库初始化完成
- [x] 所有数据表创建成功
- [x] media_assets 记录写入
- [x] streams 记录写入
- [x] job 状态为 SUCCESS
- [x] project 状态为 READY_FOR_RESEARCH

## 测试

### 运行所有测试

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

### 运行特定测试

```bash
# 文件名解析测试
python -m pytest tests/test_media_intake.py::test_parse_filename_standard -v

# 哈希测试
python -m pytest tests/test_media_intake.py::test_compute_sha256 -v

# 验证器测试
python -m pytest tests/test_media_intake.py::test_validator_no_video_stream -v
```

## 故障排查

### FFprobe 未找到

```bash
# 检查 FFprobe 是否安装
which ffprobe

# 如果未找到，重新安装
sudo apt install ffmpeg
```

### 数据库锁定

```bash
# 检查是否有进程占用数据库
lsof projects/proj_xxx/database.sqlite

# 删除锁文件（谨慎操作）
rm projects/proj_xxx/database.sqlite-wal
rm projects/proj_xxx/database.sqlite-shm
```

### 磁盘空间不足

```bash
# 检查磁盘空间
df -h /media/w/4b5b3535-4600-43ba-9b4e-71a83d1d6e43

# 清理临时文件
rm -rf /tmp/filmdub_uploads/*
```

## 下一步

Module 01 完成后，项目状态变为 `READY_FOR_RESEARCH`，可以继续：

**Module 02: Research Worker** - 媒体研究模块

- 联网搜索影视资料（IMDb、TMDB、Wikipedia）
- 识别剧名、季、集
- 收集演员、角色信息
- 建立背景知识库

## 注意事项

1. **原始文件永不修改**：所有处理都基于原始文件的副本
2. **幂等性设计**：重复导入相同文件会返回已有记录
3. **串行执行**：Module 01 不依赖任何 AI 模型，纯 CPU 处理
4. **原子写入**：所有清单文件使用临时文件 + 重命名确保完整性
5. **可追溯性**：所有操作都记录在 job_events 表中

## 配置说明

`.env` 文件主要配置项：

```bash
# 项目存储基础目录（重要：确保有足够空间）
PROJECTS_BASE_DIR=./projects

# 最大上传文件大小（GB）
UPLOAD_MAX_FILE_SIZE_GB=100

# 临时上传目录
UPLOAD_TEMP_DIR=/tmp/filmdub_uploads

# 数据库 URL 模板
DATABASE_URL=sqlite+aiosqlite:///$PROJECTS_BASE_DIR/{project_id}/database.sqlite

# API 配置
API_HOST=0.0.0.0
API_PORT=8000

# 日志级别
LOG_LEVEL=INFO

# FFmpeg 路径
FFPROBE_PATH=ffprobe
FFMPEG_PATH=ffmpeg
```

## 许可证

MIT
