# Ticket 017: qwen-tts Service 健康检查与自动重启

## 状态: todo

## 优先级: 高

## 模块: Layer 0 Orchestrator

## 描述

实现 qwen-tts 服务的健康检查机制，确保服务可用性：

1. 定期健康检查（每 30 秒）
2. 服务不可用时自动重启
3. systemd 服务配置（Restart=always）
4. 事件通知（WebSocket 推送）
5. 日志记录

## 验收标准

- [ ] 健康检查服务定期检查 qwen-tts service
- [ ] 检测到服务不可用时自动重启
- [ ] systemd 服务配置正确（qwen-tts.service）
- [ ] 通过 WebSocket 推送服务状态事件
- [ ] 健康检查结果记录到日志
- [ ] 单元测试覆盖正常和异常场景

## 技术要点

1. 使用 VoiceAdapter.health_check() 检查服务
2. systemd Restart=already 配置
3. 事件类型: `qwen-tts:healthy`, `qwen-tts:unhealthy`, `qwen-tts:restarted`
4. 超时设置：5 秒

## 依赖

- Ticket 016: Adapter 层实现（已完成）
- Ticket 015: WebSocket 实时通信（已完成）

## 预估工作量

1-2 天
