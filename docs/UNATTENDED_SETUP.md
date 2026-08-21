# 无人值守开发系统（Unattended Dev System）

用 Pi 编码代理长期自主开发本仓库的完整基础设施。任何机器克隆本仓库后即可复刻。

## 架构

```
w 电脑
├── tmux 会话 aifanyi
│   └── scripts/pi-unattended.sh      ← 驱动：循环推进工单
│       └── pi --provider ... -c -p       每轮自动 commit + push GitHub
└── cron（*/10 * * * *）
    └── scripts/watchdog.sh           ← 看门：
        ├── 驱动活着？日志 40 分钟没动？→ 记录观察
        ├── 驱动死了？→ 自动重启（从工单断点续跑）
        └── 全部完成(ALL_DONE)？→ 不再干预
```

## 组件

| 文件 | 职责 |
|------|------|
| `.claude/KICKOFF.md` | 开工提示词：必读文档、to-spec→to-tickets→implement→code-review 工作流、硬约束 |
| `scripts/pi-unattended.sh` | 驱动循环：首轮 kickoff，之后每轮「领工单→实施→测试→commit→push」 |
| `scripts/watchdog.sh` | cron 每 10 分钟自检，驱动挂了自动拉起 |

## 额度策略

1. 主力：`zai-coding-cn/glm-4.7`（订阅制，5 小时窗口重置）
2. 兜底：`deepseek/deepseek-v4-pro`（按量付费）——zai 额度尽自动切换
3. 双尽：每 10 分钟轮询，等 zai 下一个重置窗口

## 启动 / 恢复

```bash
# 前置：pi 已安装且 ~/.pi/agent/auth.json 配好 provider；GitHub SSH key 可推送
tmux new -s aifanyi '~/AI-FanYi/scripts/pi-unattended.sh'

# 安装看门狗（幂等）
( crontab -l 2>/dev/null | grep -v watchdog.sh ; echo "*/10 * * * * $HOME/AI-FanYi/scripts/watchdog.sh" ) | crontab -
```

断点恢复机制：`.claude/KICKOFF_DONE` 存在则跳过开工阶段；工单状态落盘 `docs/tickets/*.md`，重启后从断点继续。

## 监控

```bash
tail -f ~/AI-FanYi/.claude/pi-driver.log    # 干活日志
tail ~/AI-FanYi/.claude/watchdog.log        # 看门狗事件
tmux attach -t aifanyi                      # 围观（Ctrl+B D 离开）
# 或直接看 GitHub 提交流
```

## 手动停止

```bash
tmux attach -t aifanyi   # 然后 Ctrl+C
crontab -l | grep -v watchdog.sh | crontab -   # 停看门狗
```
