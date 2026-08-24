# Ticket 034: M02 场景/镜头/黑屏检测

## 状态: done

## 优先级: P2

## 模块: M02 Media Analysis

## 描述

实现 M02 媒体分析的场景/镜头/黑屏检测：基于 FFmpeg/PyAV 的场景切割、镜头变化检测、黑屏检测，输出 Scene Timeline。

参考：计划书 1 1.5 节。

## 任务清单

- [ ] 用 PyAV/FFmpeg 实现场景切割（场景变化检测）
- [ ] 实现镜头变化检测（帧间差异）
- [ ] 实现黑屏检测
- [ ] 输出 Scene Timeline（对齐时间轴）
- [ ] 编写单元测试（test_scene_detection.py）

## 验收标准

- 能对测试视频输出场景/镜头/黑屏时间线
- 测试通过
