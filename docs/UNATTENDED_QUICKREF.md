# 无人值守系统快速参考

## 🚀 快速启动

```bash
# 一键启动（tmux + 看门狗）
cd ~/AI-FanYi
tmux new-session -d -s aifanyi '~/AI-FanYi/scripts/pi-unattended.sh'
( crontab -l 2>/dev/null | grep -v watchdog.sh ; \
  echo "*/10 * * * * $HOME/AI-FanYi/scripts/watchdog.sh" ) | crontab -
```

## 🛑 快速停止

```bash
# 停止驱动
tmux kill-session -t aifanyi

# 停止看门狗
crontab -l | grep -v watchdog.sh | crontab -
```

## 📊 状态查看

```bash
# 驱动日志（实时）
tail -f ~/.claude/pi-driver.log

# 看门狗日志
tail ~/.claude/watchdog.log

# 当前任务状态
cat .claude/current-task.yaml

# 工单列表
ls -la docs/tickets/
```

## 🔄 恢复操作

```bash
# 正常重启（断点续跑）
tmux kill-session -t aifanyi
tmux new-session -d -s aifanyi '~/AI-FanYi/scripts/pi-unattended.sh'

# 强制重新开始（清空进度）
rm -f .claude/KICKOFF_DONE
rm -f docs/tickets/*.md
tmux new-session -d -s aifanyi '~/AI-FanYi/scripts/pi-unattended.sh'

# 从特定工单恢复
# 编辑 docs/tickets/xxx.md，将状态改为 "todo"
# 然后重启驱动
```

## 🔍 故障诊断

```bash
# 检查驱动进程
pgrep -f "scripts/pi-unattended[.]sh"

# 检查锁文件
ls -la /tmp/aifanyi-driver.lock

# 检查 tmux 会话
tmux ls

# 检查 Provider 状态
# 替换 YOUR_API_KEY
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.z.ai/api/coding/paas/v4/models"
```

## 📁 核心文件

| 文件 | 作用 |
|------|------|
| `scripts/pi-unattended.sh` | 主驱动 v7 |
| `scripts/watchdog.sh` | 看门狗 |
| `.claude/auto-config.json` | 自动编排器配置 |
| `.claude/KICKOFF.md` | 开工提示词 |
| `.claude/RECOVERY.md` | 恢复提示词 |
| `.claude/pi-driver.log` | 驱动日志 |
| `.claude/watchdog.log` | 看门狗日志 |

## ⚙️ 关键配置

```json
// .claude/auto-config.json
{
  "check_interval": 300,      // 检查间隔（秒）
  "quota_threshold": 80,      // 额度阈值（%）
  "auto_commit": false        // 自动提交
}
```

```bash
# Provider 轮换策略
PROVIDERS=("zai-coding-cn/glm-4.7" "deepseek/deepseek-v4-flash")

# 熔断阈值
零输出熔断：900秒（15分钟）
卡死检测：2700秒（45分钟）
Provider轮换失败：900秒（15分钟）
```

## 🎯 工作流程

```
KICKOFF（首轮）
  ↓
主循环
  ├─ 领工单
  ├─ 实施 (pi agent)
  ├─ pytest 验收
  ├─ git commit + push
  ├─ 更新工单状态
  ├─ 完成检测
  └─ 错误处理（熔断/轮换）
  ↓
ALL_DONE → 结束
```

## 💡 常用命令

```bash
# 查看驱动日志最后100行
tail -100 .claude/pi-driver.log

# 查看包含ERROR的日志
grep ERROR .claude/pi-driver.log

# 查看今天的提交
git log --since="today" --oneline

# 查看未推送的提交
git log origin/main..HEAD --oneline

# 手动运行测试
.venv/bin/python -m pytest src/filmdub/tests/ -v

# 查看工单状态
grep -h "状态:" docs/tickets/*.md

# 统计工单完成情况
echo "TODO: $(grep -l "状态: todo" docs/tickets/*.md | wc -l)"
echo "DONE: $(grep -l "状态: done" docs/tickets/*.md | wc -l)"
```

## 📞 快速求助

```bash
# 查看完整文档
cat docs/UNATTENDED_SYSTEM_COMPLETE.md

# 查看自动编排器指南
cat AUTO_ORCHESTRATOR_GUIDE.md

# 查看日志找问题
tail -200 .claude/pi-driver.log | grep -E "ERROR|WARNING|⚠️|❌"
```

## 🔐 安全检查

```bash
# 检查 SSH 连接 GitHub
ssh -T git@github.com

# 检查 provider 密钥
cat ~/.pi/agent/auth.json

# 检查 cron 任务
crontab -l | grep watchdog

# 检查磁盘空间
df -h

# 检查内存使用
free -h
```

---

**版本**: v7 | **更新**: 2026-08-23
