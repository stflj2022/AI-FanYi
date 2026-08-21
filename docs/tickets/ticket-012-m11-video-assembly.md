# Ticket 012: M11 视频组装与最终编码

##状态: todo（阶段2复验：需真实实现+pytest通过）

## 优先级: 高

## 模块: M11 - Video Assembly

## 描述

实现 M11 的视频组装和最终编码功能，将合成音频与原始视频合并，生成最终配音视频。

## 任务清单

- [ ] 创建 `src/filmdub/workers/video_assembly/` 目录结构
- [ ] 创建 `src/filmdub/workers/video_assembly/config.py` - 配置
- [ ] 创建 `src/filmdub/workers/video_assembly/assembler.py` - 视频组装器
  - [ ] VideoAssembler 类
  - [ ] assemble_video() - 组装视频
  - [ ] _replace_audio() - 替换音频轨道
  - [ ] _sync_audio_video() - 音视频同步
  - [ ] _embed_subtitles() - 嵌入字幕
  - [ ] _encode_video() - 编码视频
- [ ] 集成 FFmpeg
  - [ ] 使用 ffmpeg-python 或 subprocess
  - [ ] 实现音频替换
  - [ ] 实现音视频同步
  - [ ] 实现字幕嵌入
- [ ] 创建 `src/filmdub/workers/video_assembly/models.py` - 数据模型
- [ ] 创建 `src/filmdub/workers/video_assembly/main.py` - Worker 入口
- [ ] 实现进度回调
- [ ] 实现错误处理和重试
- [ ] 编写单元测试
- [ ] 编写视频处理测试

## 依赖

- Ticket 001: 数据库模型
- Ticket 002: Artifact Registry
- Ticket 011: M09 语音合成

## 输出

- M11 视频组装器实现
- FFmpeg 集成
- 测试文件

## 验收标准

1. 可以成功替换音频
2. 音视频同步正确
3. 字幕嵌入正确
4. 编码参数合理
5. 测试通过

## 参考 ADR

- ADR 0021: M11 视频组装
- specs/m06-m14-overview.md
