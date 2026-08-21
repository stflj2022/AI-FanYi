# 自动编排器使用指南

自动编排器是为了解决**长期开发任务中 API 额度用尽导致任务中断**的问题而设计的。它可以在无人值守的情况下：
- 自动监控 API 额度
- 在额度快用完时自动保存进度
- 等待额度重置
- 生成恢复指令

---

## 🎯 核心功能

### 1. 额度监控
- 每 5 分钟检查一次 API 额度使用情况
- 当使用量超过 80% 时自动触发保存

### 2. 自动保存
- 保存当前任务进度
- 生成上下文摘要
- 创建恢复指令

### 3. 智能等待
- 计算距离额度重置的剩余时间
- 定期报告等待进度
- 额度重置后自动恢复

### 4. 恢复机制
- 生成详细的恢复指令
- 保留完整的任务上下文
- 支持中断后继续

---

## 🚀 快速开始

### 方式 1：使用 Makefile（推荐）

```bash
# 启动自动编排器（进入监控模式）
make auto-start

# 检查额度和状态
make auto-check

# 手动保存检查点
make auto-save PHASE=module-04 MESSAGE="完成音频分析" NEXT="开始说话人分离" CONTEXT="VAD检测已完成，共检测到523个语音段"

# 查看恢复指令
make auto-resume

# 等待额度重置
make auto-wait
```

### 方式 2：直接调用脚本

```bash
# 启动 Python 编排器
python3 .claude/scripts/auto-orchestrator.py

# 只检查额度
python3 .claude/scripts/auto-orchestrator.py --check

# 保存检查点
python3 .claude/scripts/auto-orchestrator.py --save <phase> "<message>" "<next>" "<context>"

# 生成恢复指令
python3 .claude/scripts/auto-orchestrator.py --resume

# 等待重置
python3 .claude/scripts/auto-orchestrator.py --wait
```

### 方式 3：使用 Bash 脚本

```bash
# 启动监控
bash .claude/scripts/auto-task-runner.sh monitor

# 检查额度
bash .claude/scripts/auto-task-runner.sh check

# 保存检查点
bash .claude/scripts/auto-task-runner.sh checkpoint <phase> "<message>" "<resume-prompt>"

# 生成恢复指令
bash .claude/scripts/auto-task-runner.sh resume-prompt
```

---

## 📋 完整工作流程

### 场景 1：开发新模块（无人值守模式）

```bash
# 1. 启动自动编排器
make auto-start

# 2. 在另一个终端继续开发
python src/filmdub/cli.py project create --title "新作品" --target-language zh-CN

# 3. 编排器会在后台自动监控额度
#    - 超过 80% 时自动保存
#    - 生成恢复指令
#    - 等待重置

# 4. 额度重置后，查看恢复指令
make auto-resume > .claude/RESUME.txt

# 5. 继续开发
cat .claude/RESUME.txt  # 查看恢复指令
```

### 场景 2：手动保存进度（推荐用于关键节点）

```bash
# 完成一个重要功能后
make auto-save \
  PHASE="module-04-vad" \
  MESSAGE="完成 VAD（语音活动检测）模块" \
  NEXT="实现 Speaker Diarization" \
  CONTEXT="已实现基于 pyannote.audio 的 VAD，测试视频处理完成，检测到 523 个语音段，置信度 0.87"
```

### 场景 3：保存并等待重置

```bash
# 检测到额度快用完，一次性保存并等待
make checkpoint-and-wait \
  PHASE="module-05-speaker-mapping" \
  MESSAGE="说话人映射算法实现到 50%" \
  NEXT="完成映射算法并测试" \
  CONTEXT="已完成数据结构设计和基础算法，待优化匹配精度"

# 这个命令会：
# 1. 保存检查点
# 2. 等待额度重置
# 3. 生成恢复指令
```

---

## ⚙️ 配置

### 自动编排器配置文件

创建 `.claude/auto-config.json`：

```json
{
  "check_interval": 300,
  "quota_threshold": 80,
  "max_cycles": null,
  "auto_commit": false,
  "notification": {
    "enabled": false,
    "webhook": null
  }
}
```

#### 配置说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `check_interval` | 300 | 检查间隔（秒），默认 5 分钟 |
| `quota_threshold` | 80 | 触发保存的额度阈值（%） |
| `max_cycles` | null | 最大循环次数，null 表示无限 |
| `auto_commit` | false | 是否自动提交到 Git |
| `notification.enabled` | false | 是否启用通知 |
| `notification.webhook` | null | 通知 Webhook URL |

### 环境变量

```bash
# .env 文件中配置
QUOTA_CHECK_INTERVAL=300      # 检查间隔（秒）
QUOTA_THRESHOLD=80            # 触发阈值（%）
AUTO_COMMIT=false             # 自动提交
```

---

## 📊 生成的文件

自动编排器会在 `.claude/` 目录下生成以下文件：

```
.claude/
├── auto-config.json           # 配置文件
├── current-task.yaml          # 当前任务状态
├── context-summary.md         # 上下文摘要
├── quota-usage.json           # 额度使用记录
├── checkpoints/               # 检查点目录
│   └── checkpoint_20260821_090000.json
├── waiting-for-reset.json     # 等待标记（等待时生成）
├── RESUME_INSTRUCTION.txt     # 恢复指令
└── orchestrator.log           # 编排器日志
```

---

## 🔍 查看状态

### 查看当前任务状态

```bash
# 使用 Makefile
make task-status

# 或直接查看
cat .claude/current-task.yaml
cat .claude/context-summary.md
cat .claude/quota-usage.json
```

### 查看日志

```bash
# 编排器日志
tail -f .claude/orchestrator.log

# 检查点历史
ls -lh .claude/checkpoints/

# 最新检查点
cat .claude/checkpoints/$(ls -t .claude/checkpoints/ | head -1)
```

---

## 💡 实际使用示例

### 示例 1：开发 M04 Audio Analysis

```bash
# 终端 1：启动自动编排器
make auto-start
# 输出：
# [2026-08-21 09:00:00] ℹ️  启动自动任务编排器
# [2026-08-21 09:00:00] ℹ️  检查间隔: 300秒
# [2026-08-21 09:00:00] ℹ️  额度阈值: 80%
# [2026-08-21 09:00:00] ℹ️  当前额度: 15.0% (150000/1000000)
# [2026-08-21 09:05:00] ℹ️  当前额度: 35.0% (350000/1000000)
# [2026-08-21 09:10:00] ℹ️  当前额度: 55.0% (550000/1000000)
# [2026-08-21 09:15:00] ℹ️  当前额度: 75.0% (750000/1000000)
# [2026-08-21 09:20:00] ⚠️  当前额度: 82.0% (820000/1000000)
# [2026-08-21 09:20:00] ⚠️  额度超过阈值，保存进度并等待重置
# [2026-08-21 09:20:00] ✅ 检查点已保存: quota-checkpoint
# [2026-08-21 09:20:00] ℹ️  等待额度重置: 4小时30分钟

# 终端 2：继续开发
python src/filmdub/cli.py audio analyze proj_266ef70deb92

# ... 额度用完，中断 ...

# 终端 2：查看恢复指令
make auto-resume
# 输出完整的恢复指令

# 终端 2：等额度重置后，继续开发
python src/filmdub/cli.py audio analyze proj_266ef70deb92
```

### 示例 2：手动管理长期任务

```bash
# 开始一个长期任务
make task-start TASK_ID=implement-m04-m05

# 完成第一步后保存
make auto-save \
  PHASE="m04-vad-complete" \
  MESSAGE="完成 VAD 模块实现和测试" \
  NEXT="开始 Speaker Diarization" \
  CONTEXT="使用 pyannote.audio，准确率 87%，处理时间 3分钟/小时视频"

# 继续开发...

# 完成第二步后保存
make auto-save \
  PHASE="m04-diarization-complete" \
  MESSAGE="完成 Speaker Diarization" \
  NEXT="开始 Speaker Embeddings 生成" \
  CONTEXT "识别到 5 个说话人，置信度 0.82"

# 查看状态
make task-status

# 暂时中断，准备恢复
make auto-resume > .claude/RESUME.txt
git add .claude/
git commit -m "checkpoint: 保存 M04 进度"
```

---

## 🛠️ 高级用法

### 自定义检查点脚本

创建 `.claude/scripts/custom-checkpoint.sh`：

```bash
#!/bin/bash
PHASE=$1
MESSAGE=$2

# 保存代码状态
git add .
git commit -m "[checkpoint] $PHASE: $MESSAGE"

# 保存项目状态
cp projects/proj_*/database.sqlite backups/db_$(date +%Y%m%d_%H%M%S).sqlite

# 调用自动编排器
make auto-save PHASE="$PHASE" MESSAGE="$MESSAGE" NEXT="待定"
```

使用：

```bash
bash .claude/scripts/custom-checkpoint.sh "m04-complete" "完成音频分析模块"
```

### 集成到开发工作流

在 `~/.bashrc` 或 `~/.zshrc` 中添加别名：

```bash
# 自动编排器快捷命令
alias aostart='make auto-start'
alias aosave='make auto-save'
alias aostatus='make task-status'
alias aoresume='make auto-resume'
```

使用：

```bash
aostart        # 启动编排器
aosave phase "消息" "下一步" "上下文"  # 保存
aostatus       # 查看状态
aoresume       # 恢复
```

---

## ⚠️ 注意事项

### 1. 额度计算

编排器使用**估算**方式计算额度：

```python
# 假设平均每分钟使用 5000 tokens
tokens_used = duration_minutes * 5000
```

如果需要精确计算，可以修改 `auto-orchestrator.py` 中的 `estimate_tokens()` 方法。

### 2. 等待时间

智谱 API 额度通常每 5 小时重置一次。如果重置时间不同，需要修改配置：

```json
{
  "reset_interval_hours": 5
}
```

### 3. Git 自动提交

启用自动提交需要确保：

```bash
# 配置 Git 用户信息
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 4. 通知功能

如果需要通知（如 Telegram、企业微信），配置 Webhook：

```json
{
  "notification": {
    "enabled": true,
    "webhook": "https://api.telegram.org/bot<token>/sendMessage?chat_id=<chat_id>"
  }
}
```

---

## 🐛 故障排除

### 问题 1：Python 未找到

```bash
# 检查 Python 版本
python3 --version

# 如果没有 Python 3，安装它
sudo apt install python3 python3-pip
```

### 问题 2：权限错误

```bash
# 添加执行权限
chmod +x .claude/scripts/*.sh
chmod +x .claude/scripts/*.py
```

### 问题 3：额度文件损坏

```bash
# 删除额度文件，会自动重新创建
rm .claude/quota-usage.json
```

### 问题 4：编排器卡住

```bash
# 查看日志
tail -f .claude/orchestrator.log

# 手动停止
pkill -f auto-orchestrator.py

# 清理等待标记
rm .claude/waiting-for-reset.json
```

---

## 📚 相关文档

- [Makefile 命令](../Makefile) - 所有可用命令
- [快速开始](QUICKSTART.md) - 项目快速上手
- [迁移说明](MIGRATION.md) - 代码迁移说明
- [架构设计](docs/adr/) - 24 ADR 设计文档

---

## 🆘 需要帮助？

- 查看日志: `tail -f .claude/orchestrator.log`
- 查看状态: `make task-status`
- 查看恢复指令: `make auto-resume`

---

**更新日期**: 2026-08-21
**版本**: 1.0.0
**作者**: AI Assistant
