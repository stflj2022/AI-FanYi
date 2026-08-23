# Ticket 021: M12 视频封装

## 状态: done

## 优先级: 高

## 模块: M12 - Video Assembly & Final Encoding

## 描述

实现 M12 视频封装模块，将中文对白、背景音、字幕组装成最终的 mp4 视频。

## 任务清单

- [ ] 创建 `src/filmdub/workers/video_encapsulation/` 目录
- [ ] 实现 VideoEncapsulationWorker 类
- [ ] 实现视频编码功能（FFmpeg 封装）
- [ ] 实现字幕嵌入功能（SRT/ASS 字幕）
- [ ] 实现多音轨混音（中文对白 + 背景音）
- [ ] 实现视频质量控制（分辨率、码率、帧率）
- [ ] 编写单元测试
- [ ] 编写集成测试

## 技术要点

1. **FFmpeg 集成**: 使用 FFmpeg 进行视频编码和封装
2. **字幕嵌入**: 支持硬字幕和软字幕两种模式
3. **音轨混音**: 合并 AI 生成的中文对白和原始背景音
4. **格式输出**: 输出标准的 mp4 (H.264 + AAC) 格式
5. **质量控制**: 支持自定义分辨率、码率、帧率

## 输入

- 中文对白音频文件（来自 M09）
- 背景音频文件（来自 M02 分离）
- 原始视频文件
- 字幕文件（SRT/ASS）

## 输出

- 最终的中文配音视频（mp4 格式）

## 依赖

- Ticket 011: M09 语音合成（已完成）
- Ticket 002: Artifact Registry（已完成）

## 验收标准

1. 能够将中文对白、背景音、字幕组装成 mp4 视频
2. 视频音画同步
3. 字幕正确显示
4. 输出视频符合广播标准
5. 单元测试通过率 > 90%
6. 集成测试通过

## 参考规范

- specs/m11-video-assembly.md（如有）
- FFmpeg 文档：https://ffmpeg.org/documentation.html
