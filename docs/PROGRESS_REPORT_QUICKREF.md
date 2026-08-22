# AI-FanYi 进度汇报系统

## 自动汇报

系统已配置为 **每半小时自动汇报一次**，汇报内容包括：

- 📊 **服务状态**：aifanyi-driver.service 运行状态、内存、CPU 使用
- 📝 **最新日志**：pi-driver.log 最后 20 行
- 🔀 **Git 状态**：最新 3 个提交、当前分支、未提交文件
- 🎫 **工单状态**：总工单数、已完成数、阻塞数
- 💻 **系统资源**：CPU、内存、磁盘使用情况

### 🖥️ 桌面通知

每次汇报完成后，系统会自动发送**桌面通知**，包含关键信息摘要：

```
📋 AI-FanYi 进度汇报 [05:54]
📊 ✅ 运行中
🔀 最新: 69c31b7 feat(adapter): implement...
🎫 工单: 0/19 完成
💻 CPU: 1.5% | 内存: 3.5Gi/16Gi
```

#### 通知行为

- ✅ **停留在桌面**：通知不会自动消失，需要手动点击关闭
- 🔄 **自动替换**：多次通报时，只保留**最近的一次**通知
- 🎨 **智能图标**：
  - **运行中**：蓝色信息图标（正常优先级）
  - **未运行**：红色错误图标（紧急优先级）

## 手动操作

### 查看最近汇报
```bash
# 查看最近 3 次汇报
~/桌面/AI-FanYi/scripts/view-reports.sh

# 查看完整汇报日志
cat ~/桌面/AI-FanYi/.claude/progress-report.log
```

### 手动触发汇报
```bash
# 立即生成一次汇报
~/桌面/AI-FanYi/scripts/progress-report.sh
```

### 管理定时器
```bash
# 查看定时器状态
systemctl --user status aifanyi-progress-report.timer

# 查看下次触发时间
systemctl --user list-timers aifanyi*

# 停止自动汇报
systemctl --user stop aifanyi-progress-report.timer

# 恢复自动汇报
systemctl --user start aifanyi-progress-report.timer

# 禁用自动汇报（重启后不自动启动）
systemctl --user disable aifanyi-progress-report.timer

# 启用自动汇报（重启后自动启动）
systemctl --user enable aifanyi-progress-report.timer
```

### 修改汇报间隔

编辑定时器配置文件：
```bash
nano ~/.config/systemd/user/aifanyi-progress-report.timer
```

修改 `OnCalendar` 行：
```ini
# 每 30 分钟（默认）
OnCalendar=*:0/30

# 每 1 小时
OnCalendar=*:0/60

# 每 15 分钟
OnCalendar=*:0/15

# 每天的 9:00, 13:00, 17:00, 21:00
OnCalendar=09:00,13:00,17:00,21:00
```

修改后重新加载：
```bash
systemctl --user daemon-reload
systemctl --user restart aifanyi-progress-report.timer
```

## 查看实时进度

除了自动汇报，你也可以实时查看：

```bash
# 附加到 tmux 会话（实时查看）
tmux attach-session -t pi
# 退出：Ctrl+B, D

# 实时跟踪日志
tail -f ~/桌面/AI-FanYi/.claude/pi-driver.log

# 查看服务状态
systemctl --user status aifanyi-driver.service

# 查看服务日志
journalctl --user -u aifanyi-driver.service -f
```

## 通知设置

### 检查通知功能
```bash
# 测试通知
notify-send --app-name="AI-FanYi" --icon="dialog-information" --urgency="normal" --expire-time=5000 "测试通知" "通知功能正常！"
```

### 如果通知没有显示

1. **检查桌面环境**：确保你正在使用支持通知的桌面环境（GNOME、KDE、XFCE 等）

2. **检查通知守护进程**：
   ```bash
   # 查看通知守护进程是否运行
   ps aux | grep -E "(dunst|xfce4-notifyd|notification-daemon|mako)"
   ```

3. **启用桌面通知设置**：
   - **GNOME**：设置 → 通知 → 启用通知
   - **KDE**：系统设置 → 通知 → 启用通知
   - **XFCE**：设置 → 通知 → 启用通知

4. **安装通知守护进程**（如果需要）：
   ```bash
   # Debian/Ubuntu
   sudo apt install dunst  # 轻量级通知守护进程
   # 或
   sudo apt install xfce4-notifyd  # XFCE 通知
   ```

#### 恢复自动消失（可选）

如果你希望通知自动消失，可以修改脚本：

```bash
nano ~/桌面/AI-FanYi/scripts/progress-report.sh
# 找到 notify-send 命令，将 --expire-time=0 改为 --expire-time=10000
```

## 文件位置

| 文件 | 路径 |
|------|------|
| 汇报脚本 | `~/桌面/AI-FanYi/scripts/progress-report.sh` |
| 查看脚本 | `~/桌面/AI-FanYi/scripts/view-reports.sh` |
| 汇报日志 | `~/桌面/AI-FanYi/.claude/progress-report.log` |
| 定时器服务 | `~/.config/systemd/user/aifanyi-progress-report.service` |
| 定时器配置 | `~/.config/systemd/user/aifanyi-progress-report.timer` |

## 示例输出

```
========================================
AI-FanYi 监督系统进度汇报
时间: 2026-08-23 05:18:02
========================================

📊 服务状态
  ✅ aifanyi-driver.service 运行中
  MainPID=138358
  MemoryCurrent=4290904064
  ActiveState=active

📝 最新日志 (最后 20 行)
  [2026-08-23 05:07:25] ✅ zai 已恢复可用，自动切回（移除临时 deepseek 标志）
  [2026-08-23 05:07:25] === ROUND 1 (zai-coding-cn/glm-4.7) ===
  [2026-08-23 05:07:25] ▶ pi 启动 (zai-coding-cn/glm-4.7)

🔀 Git 状态
  最新提交:
    f5ad981 chore(config): Settings/OrchestratorSettings 允许 .env 多余变量（extra="ignore"）
    237f899 fix(video_assembly): 合成音轨加 anullsrc 静音底床修复 amix duration=first 截断
    ...

  当前分支: main
  未提交文件:
    M .claude/.round_mark
    M .claude/KICKOFF.md
    ...

🎫 工单状态
  总工单数: 16
  已完成: 0

💻 系统资源
  CPU: 12.6% 使用
  内存: 3.5Gi/16Gi
  磁盘: 350G/453G (82%)

========================================
汇报完成
========================================
```
