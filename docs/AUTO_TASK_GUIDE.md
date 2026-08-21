# 无人值守任务执行系统

## 概述

完全自动化的任务执行系统，无需人工值守，自动处理：
- ✅ 额度监控和预警
- ✅ 自动保存进度
- ✅ 等待额度重置
- ✅ 生成恢复指令
- ✅ 循环执行

## 工作原理

```
开始任务 → 执行工作 → 定期检查额度 → 额度不足 → 自动保存进度
                                               ↓
                                           等待重置（自动）
                                               ↓
                                           生成恢复指令
                                               ↓
                                           （等待用户恢复或自动继续）
```

## 快速开始

### 方式一：完全自动监控（推荐）

```bash
# 启动自动编排器，会自动处理所有情况
make auto-start
```

编排器会：
1. 每5分钟检查一次额度
2. 额度超过80%时自动保存进度
3. 自动等待额度重置
4. 生成恢复指令

### 方式二：一键完整周期

```bash
# 执行完整周期：检查→保存→等待→生成恢复指令
make full-cycle PHASE=m01-implementation MESSAGE="完成数据库模型" NEXT="实现API端点"
```

### 方式三：手动控制各步骤

```bash
# 1. 检查额度
make auto-check

# 2. 保存进度
make auto-save PHASE=current-phase MESSAGE="当前进度" NEXT="下一步" CONTEXT="详细上下文"

# 3. 等待重置
make auto-wait

# 4. 生成恢复指令
make auto-resume
```

## 配置文件

编辑 `.claude/auto-config.json` 自定义行为：

```json
{
  "check_interval": 300,        // 检查间隔（秒）
  "quota_threshold": 80,        // 额度阈值（%）
  "max_cycles": null,           // 最大循环次数（null=无限）
  "auto_commit": false,         // 自动提交Git
  "notification": {
    "enabled": false,           // 启用通知
    "webhook": null             // Webhook URL
  }
}
```

## 完全无人值守工作流

### 场景：过夜任务

```bash
# 1. 启动自动编排器
make auto-start

# 2. 去睡觉/离开电脑

# 3. 第二天回来，查看恢复指令
cat .claude/RESUME_INSTRUCTION.txt
```

### 场景：长时间编码任务

```bash
# 1. 启动任务
make auto-start

# 2. 系统会自动：
#    - 每5分钟检查额度
#    - 接近限制时保存进度
#    - 等待重置
#    - 准备好恢复指令

# 3. 额度重置后，执行恢复指令继续
make auto-resume
```

## 恢复指令格式

系统自动生成的恢复指令：

```
╔══════════════════════════════════════════════════════════════╗
║              🤖 自动任务恢复指令 🤖                           ║
╚══════════════════════════════════════════════════════════════╝

@Claude 继续执行自动任务

══════════════════════════════════════════════════════════════
📋 当前状态
══════════════════════════════════════════════════════════════

task_id: auto-task
last_update: 2024-01-21T10:30:00Z
status: in_progress
current_phase:
  id: m01-database
  message: 完成数据库模型定义
  completed_at: 2024-01-21T10:30:00Z
next_action: 实现API端点

══════════════════════════════════════════════════════════════
📖 上下文摘要
══════════════════════════════════════════════════════════════

（详细上下文内容）

══════════════════════════════════════════════════════════════
🔧 执行指令
══════════════════════════════════════════════════════════════

请根据上下文继续执行下一步。
```

## 自动保存的文件

```
.claude/
├── auto-config.json              # 配置文件
├── current-task.yaml              # 当前任务状态
├── context-summary.md            # 上下文摘要
├── quota-usage.json              # 额度跟踪
├── RESUME_INSTRUCTION.txt        # 恢复指令（自动生成）
├── checkpoints/                   # 检查点历史
│   ├── checkpoint_20240121_103000.json
│   └── ...
└── waiting-for-reset.json        # 等待状态（等待时存在）
```

## 高级用法

### 1. 自定义检查间隔

编辑配置文件：
```json
{
  "check_interval": 180  // 3分钟检查一次
}
```

### 2. 启用自动Git提交

```json
{
  "auto_commit": true  // 每次检查点自动提交
}
```

### 3. 启用通知

```json
{
  "notification": {
    "enabled": true,
    "webhook": "https://your-webhook-url"
  }
}
```

### 4. 限制循环次数

```json
{
  "max_cycles": 10  // 最多循环10次
}
```

## 监控和调试

### 查看当前状态

```bash
make auto-status
```

### 查看日志

```bash
cat .claude/orchestrator.log
```

### 查看所有检查点

```bash
ls -la .claude/checkpoints/
```

### 查看等待状态

```bash
cat .claude/waiting-for-reset.json 2>/dev/null || echo "未在等待状态"
```

## 故障恢复

### 如果系统崩溃

检查点文件会保存所有状态，恢复步骤：

```bash
# 1. 查看最后的检查点
ls -lt .claude/checkpoints/ | head -1

# 2. 查看当前任务状态
cat .claude/current-task.yaml

# 3. 查看上下文
cat .claude/context-summary.md

# 4. 生成恢复指令
make auto-resume
```

### 如果额度检查不准确

```bash
# 手动重置额度
cat > .claude/quota-usage.json << EOF
{
  "last_reset": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "tokens_used": 0,
  "max_quota": 1000000
}
EOF
```

## 时间规划

### 智谱API额度周期

- **周期**: 每5小时重置一次
- **建议**: 在额度重置后开始大任务
- **安全阈值**: 80% 时保存进度

### 典型使用模式

```
时间线（24小时）:

00:00 - 额度重置 → 开始大任务
02:30 - 额度 80% → 自动保存进度
03:00 - 开始等待重置
05:00 - 额度重置 → 自动恢复/手动恢复
05:05 - 继续执行
07:30 - 额度 80% → 自动保存进度
08:00 - 开始等待重置
10:00 - 额度重置 → 继续
...
```

## 与 Claude Code 集成

### 在会话中使用

当上下文快满时，系统会自动：

1. 保存进度到 `.claude/`
2. 生成恢复指令
3. 显示提示信息

### 恢复新会话

```bash
# 1. 查看恢复指令
make auto-resume

# 2. 复制恢复指令

# 3. 在新 Claude 会话中粘贴恢复指令
```

## 最佳实践

### 1. 任务分解

将大任务分成小任务，每个小任务：
- 独立可执行
- 产生可验证输出
- 花费 < 2小时

### 2. 定期保存

即使额度充足，也定期保存：
```bash
# 每完成一个模块
make auto-save PHASE=module-name MESSAGE="完成模块" NEXT="下一模块"
```

### 3. 上下文维护

保持 `context-summary.md` 清晰：
- 已完成列表
- 进行中项目
- 下一步计划
- 技术决策

### 4. Git 配合

```bash
# 启用自动提交
# 编辑 auto-config.json: "auto_commit": true

# 或手动提交
git add .claude/
git commit -m "checkpoint: 进度保存"
```

## 常见问题

### Q: 额度检查准确吗？

A: 基于估算，假设平均每分钟5000 tokens。实际使用可能不同，建议保守设置阈值（70-80%）。

### Q: 等待重置期间安全吗？

A: 是的，系统会记录等待状态，即使中断也可以恢复。

### Q: 如何强制立即保存？

```bash
make auto-save PHASE=manual MESSAGE="手动保存" NEXT="继续" CONTEXT="手动保存点"
```

### Q: 如何跳过等待？

直接运行恢复指令继续，系统会在下次检查时处理额度。

## 总结

这个自动化系统让你可以：

✅ 启动任务后离开电脑
✅ 自动保存进度
✅ 自动等待额度重置
✅ 随时恢复继续
✅ 完全无人值守

开始使用：
```bash
make auto-start
```
