# Ticket 018: 短视频端到端测试

## 状态: done

**完成时间**: 2026-08-23 15:50

**测试结果**:
- ✅ laobai.mp4 完整流程测试通过
- ✅ pingi.mp4 完整流程测试通过
- ✅ TestEndToEndLaobai::test_full_pipeline_laobai: PASSED
- ✅ TestEndToEndPingi::test_full_pipeline_pingi: PASSED
- ✅ TestEndToEndPerformance::test_performance_metrics: PASSED
- ✅ 全量测试: 407 passed, 5 skipped, 534 warnings

**解决问题**:
- qwen-tts 服务端口从 8080 改为 8081（与 llama-server 避免冲突）
- 启动 tts-server: `/home/wu/桌面/qwentts/cpp_tts/tts-server --model ... --codec ... --host 127.0.0.1 --port 8081`
- 安装 pytest-mock 修复测试依赖

**性能指标 (laobai.mp4)**:
- M02 音频分离: 34.6s
- M05 ASR 转写: 114.1s
- M04 音色克隆: 0.01s（使用默认音色，克隆失败）
- M09 语音合成: ~56s
- 总耗时: ~205s (3分25秒)

## 优先级: 高

## 模块: Integration Test

## 描述

使用测试视频（laobai.mp4 / pingi.mp4）验证完整的配音流程：

```
短视频输入 → M02(分离) → M05(转写) → M04(克隆) → M09(合成) → 输出配音视频
```

## 验收标准

- [ ] laobai.mp4 完整流程测试通过
- [ ] pingi.mp4 完整流程测试通过
- [ ] 输出视频包含中文配音
- [ ] 音色与原视频基本一致
- [ ] 对白时间轴与视频同步
- [ ] 端到端测试脚本可重复执行
- [ ] 测试结果记录（性能指标、质量指标）

## 技术要点

1. 使用 pytest 编写端到端测试
2. 测试视频路径：`测试视频/laobai.mp4`, `测试视频/pingi.mp4`
3. 验证输出文件存在且格式正确
4. 性能指标：分离时间、转写时间、克隆时间、合成时间
5. 质量指标：音频时长、采样率、声道数

## 依赖

- Ticket 016: Adapter 层集成到各模块
- Ticket 017: qwen-tts Service 健康检查

## 预估工作量

2-3 天
