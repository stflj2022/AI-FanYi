#!/bin/bash
# 自动编排器快速参考卡片

cat << 'EOF'
╔══════════════════════════════════════════════════════════════════════════════╗
║                   自动编排器快速参考 (Auto Orchestrator)                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

🚀 快速命令
────────────────────────────────────────────────────────────────────────────
  make auto-start      启动自动编排器（后台监控）
  make auto-check      检查额度和状态
  make auto-save       保存检查点（需要参数）
  make auto-resume     生成恢复指令
  make auto-wait       等待额度重置
  make task-status     查看当前任务状态
  make task-quota      检查 API 额度

📝 保存检查点
────────────────────────────────────────────────────────────────────────────
  make auto-save PHASE=<阶段> MESSAGE="<描述>" NEXT="<下一步>" CONTEXT="<上下文>"

  示例:
  make auto-save \
    PHASE="m04-vad" \
    MESSAGE="完成 VAD 模块" \
    NEXT="实现 Speaker Diarization" \
    CONTEXT="准确率 87%，处理 523 个语音段"

🔄 完整周期
────────────────────────────────────────────────────────────────────────────
  make checkpoint-and-wait \
    PHASE=<阶段> \
    MESSAGE="<描述>" \
    NEXT="<下一步>" \
    CONTEXT="<上下文>"

  此命令会:
  1. 保存检查点
  2. 等待额度重置
  3. 生成恢复指令

📊 查看状态
────────────────────────────────────────────────────────────────────────────
  cat .claude/current-task.yaml      # 当前任务
  cat .claude/context-summary.md     # 上下文摘要
  cat .claude/quota-usage.json       # 额度使用
  tail -f .claude/orchestrator.log   # 实时日志

📁 生成的文件
────────────────────────────────────────────────────────────────────────────
  .claude/
  ├── auto-config.json           # 配置文件
  ├── current-task.yaml          # 任务状态
  ├── context-summary.md         # 上下文
  ├── quota-usage.json           # 额度
  ├── checkpoints/               # 检查点目录
  │   └── checkpoint_*.json
  └── orchestrator.log           # 日志

⚙️  配置文件 (.claude/auto-config.json)
────────────────────────────────────────────────────────────────────────────
  {
    "check_interval": 300,      # 检查间隔（秒）
    "quota_threshold": 80,      # 触发阈值（%）
    "max_cycles": null,         # 最大循环次数
    "auto_commit": false,       # 自动提交 Git
    "notification": {           # 通知配置
      "enabled": false,
      "webhook": null
    }
  }

💡 工作流程示例
────────────────────────────────────────────────────────────────────────────
  1. 终端 1: make auto-start           # 启动编排器
  2. 终端 2: <继续开发代码>
  3. 终端 2: make auto-save ...        # 关键节点保存
  4. [额度用完，自动中断]
  5. 终端 1: [自动等待重置]
  6. 终端 2: make auto-resume          # 查看恢复指令
  7. 终端 2: <继续开发>

🔧 直接调用脚本
────────────────────────────────────────────────────────────────────────────
  python3 .claude/scripts/auto-orchestrator.py [选项]
    --check          只检查额度
    --save ...       保存检查点
    --resume         生成恢复指令
    --wait           等待重置

  bash .claude/scripts/auto-task-runner.sh [命令]
    monitor         持续监控
    check           检查额度
    checkpoint ...  保存检查点
    resume-prompt   生成恢复指令

⚠️  注意事项
────────────────────────────────────────────────────────────────────────────
  • 额度估算基于: duration_minutes * 5000 tokens
  • 智谱 API 额度重置周期: 约 5 小时
  • 项目数据 (*.sqlite) 不会自动提交到 Git
  • 编排器只处理额度管理，不涉及模块编排

📚 更多文档
────────────────────────────────────────────────────────────────────────────
  AUTO_ORCHESTRATOR_GUIDE.md  - 完整使用指南
  QUICKSTART.md               - 项目快速开始
  MIGRATION.md                - 代码迁移说明
  docs/adr/                   - 架构设计文档

EOF
