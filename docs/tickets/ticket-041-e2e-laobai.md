# Ticket 041: laobai 端到端验证 + 测试 + 双遍 review + 推送 + 文档

## 状态: todo

## 优先级: P0

## 模块: 全平台

## 描述

端到端验收：通过 Web UI 上传 `测试视频/laobai.mp4` → 创建配音任务（选语言/质量）→ 自动走完整流水线 → 产出 final_dubbed.mp4（真实中文语音）→ Web UI 可播放/下载，QA 评分达标。

参考《计划书/ai-fanyi-web ui.txt》三十节的最终用户体验（上传→选中文/自动→开始配音→完成输出）。

## 任务清单

- [ ] 全量测试通过（新增执行引擎/展示相关测试 + 既有回归）
- [ ] 双遍 code-review（Standards + Spec）
- [ ] 提交推送 origin/main
- [ ] 更新桌面总结文档（阶段 B 成果：完整流水线 + Web UI 成品展示）

## 验收标准

- 端到端：Web UI 上传 laobai.mp4 → 自动完整流水线 → 产出最终配音视频，QA 达标
- 测试全绿，双遍 review 通过
- 已推送，桌面总结文档更新
