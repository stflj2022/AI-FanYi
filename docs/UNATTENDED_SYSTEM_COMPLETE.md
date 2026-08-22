# AI-FanYi 无人值守开发系统 - 完整说明

## 🎯 系统概述

AI-FanYi 项目配备了一套完整的**无人值守开发系统**，用于长期自动推进开发任务。该系统采用**双保险机制**：看门狗（watchdog）+ 开机自启，确保任务在异常情况下能够自动恢复。

**当前版本**: v7

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    无人值守开发系统                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  主驱动循环 (pi-unattended.sh v7)                   │  │
│  │                                                      │  │
│  │  1. 首轮 KICKOFF（仅首次）                          │  │
│  │  2. 主循环：                                        │  │
│  │     - 领工单                                        │  │
│  │     - 实施 (pi agent)                               │  │
│  │     - pytest 验收                                   │  │
│  │     - git commit + push                            │  │
│  │     - 更新工单状态                                 │  │
│  3. 完成检测 → ALL_DONE                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ▲                                │
│                            │ 监控                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  看门狗 (watchdog.sh) - 每10分钟检查               │  │
│  │                                                      │  │
│  │  • 驱动进程存活检查                                  │  │
│  │  • 卡死检测（日志60分钟无更新）                     │  │
│  │  • 自动重启（断点续跑）                             │  │
│  │  • ALL_DONE 检测 → 停止干预                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  额度管理系统                                         │  │
│  │                                                      │  │
│  │  • 主力：zai-coding-cn/glm-4.7（订阅制，5小时重置）  │  │
│  │  • 兜底：deepseek/deepseek-v4-flash（按量付费）      │  │
│  │  • 自动轮换（配额尽/故障）                           │  │
│  │  • 零输出熔断（900秒无响应）                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 核心组件

### 1. 主驱动：`scripts/pi-unattended.sh` (v7)

**功能**：主驱动循环，自动推进开发任务

**关键特性**：
- ✅ **Provider 轮换**：zai ↔ deepseek 自动切换
- ✅ **零输出熔断**：900秒无响应自动终止
- ✅ **上下文冷启动**：会话膨胀自动重启
- ✅ **Pytest 独立验收**：每轮独立验证测试
- ✅ **单例守卫**：flock 文件锁防双开
- ✅ **预防性换会话**：每8轮强制新会话
- ✅ **自动 commit + push**：每轮自动推送 GitHub

**运行流程**：

```bash
#!/bin/bash
# v7 核心逻辑

PROVIDERS=("zai-coding-cn/glm-4.7" "deepseek/deepseek-v4-flash")

# 1. 单例守卫
exec 9>"/tmp/aifanyi-driver.lock"
flock -n 9 || exit 1

# 2. 首轮 KICKOFF（仅首次）
if [ ! -f ".claude/KICKOFF_DONE" ]; then
  run_pi "$(cur)" "$(cat .claude/KICKOFF.md)"
  touch .claude/KICKOFF_DONE
fi

# 3. 主循环
while true; do
  # a) Provider 健康检查
  if ! zai_alive && deepseek_alive; then
    PI=$(( (PI+1) % 2 ))  # 切换 provider
  fi

  # b) 每8轮预防性换会话
  if [ $((N % 8)) -eq 0 ]; then
    touch .claude/FRESH_NEXT
  fi

  # c) 执行 pi agent
  run_pi "$(cur)" "$CONT_PROMPT"

  # d) 自动提交推送
  git add -A && git commit -m "chore(driver): 自动检查点"
  git push origin HEAD

  # e) 完成检测
  if done_check; then
    echo "ALL_DONE"
    break
  fi

  # f) 错误处理
  if quota_hit || ctx_hit; then
    touch .claude/ROTATE_NEXT
    PI=$(( (PI+1) % 2 ))  # 切换 provider
  fi

  sleep 30
done
```

**熔断机制**：

| 触发条件 | 检测方法 | 处理方式 |
|---------|---------|---------|
| 零输出熔断 | 900秒无输出+CPU静默 | 标记 ROTATE_NEXT，终止当前轮次 |
| 配额耗尽 | 日志包含 quota/429/余额不足 | 标记 ROTATE_NEXT，切换 provider |
| 上下文满 | 日志包含 context length exceeded | 开新会话 (FRESH_NEXT) |
| Provider 死亡 | HTTP 健康检查失败 | 切换到备用 provider |
| 全部阵亡 | 所有 provider 不可用 | 睡 900秒后重试 |

---

### 2. 看门狗：`scripts/watchdog.sh`

**功能**：cron 每10分钟检查驱动状态，异常自动恢复

**检查项**：
1. **ALL_DONE 检测**：任务全部完成则不再干预
2. **进程存活检查**：`pgrep -f "scripts/pi-unattended.sh"`
3. **卡死检测**：日志文件 60 分钟无更新

**自动恢复逻辑**：

```bash
#!/bin/bash
# watchdog.sh 核心逻辑

LOG="$REPO/.claude/pi-driver.log"

# 1. 已全部完成 → 不再干预
if tail -50 "$LOG" | grep -q "ALL_DONE"; then
  exit 0
fi

# 2. 驱动进程存活检查
if pgrep -f "scripts/pi-unattended[.]sh" >/dev/null; then
  # 卡死检测：日志 60 分钟无更新
  AGE=$(( $(date +%s) - $(stat -c %Y "$LOG") ))
  if [ $AGE -gt 2700 ]; then  # 45分钟
    PIPID=$(pgrep -f "^timeout 7200 pi" | head -1)
    if [ -n "$PIPID" ]; then
      # 杀掉卡死的 pi 轮次，让驱动自动进下一轮
      pkill -P "$PIPID"
      kill "$PIPID"
    fi
  fi
  exit 0
fi

# 3. 死了 → 自动重启
log "🚨 驱动未在运行 → 自动重启"
tmux kill-session -t aifanyi 2>/dev/null
tmux new-session -d -s aifanyi "$SCRIPT"
```

---

### 3. 自动任务编排器：`.claude/scripts/auto-orchestrator.py`

**功能**：额度监控、进度保存、等待重置

**核心能力**：

| 功能 | 说明 |
|------|------|
| **额度监控** | 每5分钟检查一次，超过80%触发保存 |
| **自动保存** | 保存任务进度、上下文摘要、恢复指令 |
| **智能等待** | 计算重置时间，定期报告进度 |
| **恢复机制** | 生成详细恢复指令，支持断点续跑 |
| **Git 集成** | 可选的自动提交功能 |

**配置文件**：`.claude/auto-config.json`

```json
{
  "check_interval": 300,      // 检查间隔（秒）
  "quota_threshold": 80,      // 触发阈值（%）
  "max_cycles": null,         // 最大循环次数
  "auto_commit": false,       // 自动提交
  "notification": {
    "enabled": false,
    "webhook": null
  }
}
```

**使用方式**：

```bash
# 启动监控
python3 .claude/scripts/auto-orchestrator.py

# 检查额度
python3 .claude/scripts/auto-orchestrator.py --check

# 保存检查点
python3 .claude/scripts/auto-orchestrator.py --save <phase> <message> <next> <context>

# 等待重置
python3 .claude/scripts/auto-orchestrator.py --wait
```

---

## 🚀 启动与恢复

### 首次启动

```bash
# 1. 确保 pi 已安装且配置好 provider
pi --list-models

# 2. 确保 GitHub SSH key 可推送
ssh -T git@github.com

# 3. 启动驱动（tmux 会话）
tmux new -s aifanyi '~/AI-FanYi/scripts/pi-unattended.sh'

# 4. 安装看门狗（cron 每10分钟）
( crontab -l 2>/dev/null | grep -v watchdog.sh ; \
  echo "*/10 * * * * $HOME/AI-FanYi/scripts/watchdog.sh" ) | crontab -
```

### 断点恢复

**自动恢复机制**：
- `.claude/KICKOFF_DONE` 存在 → 跳过开工阶段
- 工单状态落盘 `docs/tickets/*.md` → 从断点继续
- `.claude/FRESH_NEXT` → 开新会话（不加载历史上下文）

**手动恢复**：

```bash
# 方法1：直接重启驱动
tmux kill-session -t aifanyi
tmux new-session -d -s aifanyi '~/AI-FanYi/scripts/pi-unattended.sh'

# 方法2：强制从首轮开始
rm -f .claude/KICKOFF_DONE
rm -f docs/tickets/*.md
tmux new-session -d -s aifanyi '~/AI-FanYi/scripts/pi-unattended.sh'

# 方法3：从特定工单恢复
# 编辑 docs/tickets/xxx.md，将状态改为 "todo"
# 然后重启驱动
```

---

## 📊 监控与日志

### 实时监控

```bash
# 1. 查看驱动日志
tail -f ~/AI-FanYi/.claude/pi-driver.log

# 2. 查看看门狗日志
tail ~/AI-FanYi/.claude/watchdog.log

# 3. 围观 tmux 会话
tmux attach -t aifanyi  # Ctrl+B D 离开

# 4. 查看 GitHub 提交流
git log --oneline origin/main..HEAD
```

### 状态检查

```bash
# 驱动进程状态
pgrep -f "scripts/pi-unattended[.]sh"

# tmux 会话状态
tmux ls

# 工单状态
ls -la docs/tickets/
cat docs/tickets/*.md | grep -E "状态:|status:"

# 额度状态
cat .claude/quota-usage.json
```

### 日志文件说明

| 日志文件 | 内容 | 用途 |
|---------|------|------|
| `.claude/pi-driver.log` | 驱动主循环日志 | 查看每轮执行情况 |
| `.claude/watchdog.log` | 看门狗事件日志 | 查看重启历史 |
| `.claude/orchestrator.log` | 自动编排器日志 | 查看额度监控 |
| `.claude/current-task.yaml` | 当前任务状态 | 断点恢复依据 |
| `.claude/context-summary.md` | 上下文摘要 | 恢复时参考 |

---

## 🛑 停止系统

### 完整停止

```bash
# 1. 停止驱动
tmux attach -t aifanyi  # 然后 Ctrl+C
# 或
tmux kill-session -t aifanyi

# 2. 停止看门狗
crontab -l | grep -v watchdog.sh | crontab -

# 3. 清理锁文件
rm -f /tmp/aifanyi-driver.lock
```

### 临时暂停

```bash
# 方法1：暂停 tmux 会话
tmux detach -t aifanyi

# 方法2：创建停止标记
touch .claude/PAUSE
# 驱动会检测到此文件并停止
# 恢复时删除文件即可
rm .claude/PAUSE
```

---

## 🔧 配置与调优

### Provider 配置

编辑 `~/.pi/agent/auth.json`：

```json
{
  "zai-coding-cn": {
    "type": "api_key",
    "key": "你的zai密钥"
  },
  "deepseek": {
    "type": "api_key",
    "key": "你的deepseek密钥"
  }
}
```

### 熔断阈值调整

编辑 `scripts/pi-unattended.sh`：

```bash
# 零输出熔断时间（默认900秒=15分钟）
if [ "$zeros" -ge 30 ]; then  # 30 * 30秒 = 900秒

# 卡死检测时间（默认2700秒=45分钟）
if [ $AGE -gt 2700 ]; then

# Provider 轮换失败重试间隔（默认900秒=15分钟）
sleep 900
```

### 自动编排器配置

编辑 `.claude/auto-config.json`：

```json
{
  "check_interval": 300,        // 改为 180 = 3分钟
  "quota_threshold": 70,        // 改为 70% 更早保存
  "auto_commit": true,         // 启用自动提交
  "notification": {
    "enabled": true,
    "webhook": "https://api.telegram.org/..."
  }
}
```

---

## 🐛 故障排除

### 问题1：驱动启动失败

```bash
# 检查锁文件
ls -la /tmp/aifanyi-driver.lock

# 手动清理
rm -f /tmp/aifanyi-driver.lock

# 重新启动
tmux new-session -d -s aifanyi '~/AI-FanYi/scripts/pi-unattended.sh'
```

### 问题2：看门狗频繁重启

```bash
# 查看看门狗日志
tail -50 .claude/watchdog.log

# 检查驱动日志
tail -100 .claude/pi-driver.log | grep ERROR

# 可能原因：
# - Provider 配额耗尽
# - 网络问题
# - 驱动代码bug

# 解决方案：
# 1. 检查 Provider 状态
curl -H "Authorization: Bearer $ZAI_KEY" \
  "https://api.z.ai/api/coding/paas/v4/models"

# 2. 检查网络
ping api.z.ai
ping api.deepseek.com
```

### 问题3：测试一直失败

```bash
# 手动运行测试
cd ~/AI-FanYi
.venv/bin/python -m pytest src/filmdub/tests/ -v

# 查看具体失败
.venv/bin/python -m pytest src/filmdub/tests/test_media_intake.py -v

# 修复后标记工单为 done
# 编辑 docs/tickets/xxx.md
# 将状态改为 "done"
```

### 问题4：GitHub push 失败

```bash
# 检查 SSH 配置
ssh -T git@github.com

# 检查远程仓库
git remote -v

# 手动推送
git push origin HEAD

# 如果权限问题，重新配置 SSH
ssh-keygen -t ed25519
cat ~/.ssh/id_ed25519.pub
# 添加到 GitHub Settings → SSH Keys
```

---

## 📈 性能优化

### 1. 减少不必要的轮换

```bash
# 如果 zai 额度充足，减少对 deepseek 的依赖
# 编辑 pi-unattended.sh，修改健康检查逻辑
primary_alive() {
  # 改为：仅当 zai 确实不可用时才切换
  [ "$PI" -ne 0 ] && zai_alive && return 0
  return 1
}
```

### 2. 优化 pytest 时间

```bash
# 使用 pytest-xdist 并行测试
pip install pytest-xdist

# 修改 pi-unattended.sh 中的测试命令
pytest src/filmdub/tests/ -q -n auto
```

### 3. 减少日志大小

```bash
# 日志轮转
# 在 pi-unattended.sh 中添加
LOG_SIZE=$(stat -c %s "$LOG")
if [ "$LOG_SIZE" -gt 10485760 ]; then  # 10MB
  mv "$LOG" "$LOG.$(date +%Y%m%d_%H%M%S)"
  touch "$LOG"
fi
```

---

## 📚 相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 自动编排器指南 | `AUTO_ORCHESTRATOR_GUIDE.md` | 详细使用说明 |
| 无人值守设置 | `docs/UNATTENDED_SETUP.md` | 系统架构说明 |
| 自动任务指南 | `docs/AUTO_TASK_GUIDE.md` | 任务管理 |
| 快速开始任务 | `docs/QUICK_START_TASKS.md` | 工单系统 |
| 恢复策略 | `docs/RESUME_STRATEGY.md` | 断点恢复 |

---

## 🎯 最佳实践

1. **定期检查状态**：每天查看一次日志，确保系统正常运行
2. **保持 GitHub 同步**：定期 `git pull`，避免冲突
3. **监控 Provider 额度**：提前续费，避免中断
4. **备份关键数据**：定期备份 `docs/tickets/` 和 `.claude/`
5. **测试驱动开发**：确保每次提交都有测试覆盖

---

## 📞 支持与帮助

**日志位置**：
- 驱动日志：`~/.claude/pi-driver.log`
- 看门狗日志：`~/.claude/watchdog.log`
- 编排器日志：`~/.claude/orchestrator.log`

**快速命令**：
```bash
# 查看状态
make task-status

# 查看日志
tail -f .claude/pi-driver.log

# 手动重启
tmux kill-session -t aifanyi
tmux new-session -d -s aifanyi '~/AI-FanYi/scripts/pi-unattended.sh'
```

---

**系统版本**: v7
**文档更新**: 2026-08-23
**维护者**: AI Assistant
