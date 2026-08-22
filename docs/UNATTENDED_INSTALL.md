# AI-FanYi 无人值守开发系统 - 安装指南

## 快速安装

```bash
# 进入项目目录
cd ~/桌面/AI-FanYi

# 运行安装脚本
./scripts/install-unattended.sh
```

## 安装内容

安装脚本会自动配置以下组件：

### 1. 核心服务

| 服务 | 说明 | 运行方式 |
|------|------|----------|
| **aifanyi-driver.service** | 主驱动服务，自动推进开发任务 | 持续运行，自动重启 |
| **aifanyi-watchdog.timer** | 看门狗，监控并恢复异常 | 每10分钟检查 |
| **aifanyi-progress-report.timer** | 进度汇报，桌面通知 | 每30分钟汇报 |

### 2. 脚本文件

| 脚本 | 说明 |
|------|------|
| `scripts/pi-unattended.sh` | 主驱动循环脚本 |
| `scripts/progress-report.sh` | 进度汇报脚本 |
| `scripts/view-reports.sh` | 查看汇报历史 |
| `scripts/install-unattended.sh` | 安装脚本 |
| `scripts/uninstall-unattended.sh` | 卸载脚本 |

### 3. 系统配置

| 配置 | 路径 |
|------|------|
| systemd 服务 | `~/.config/systemd/user/aifanyi-*.service` |
| systemd 定时器 | `~/.config/systemd/user/aifanyi-*.timer` |
| 日志文件 | `~/.claude/pi-driver.log` |
| 汇报日志 | `~/.claude/progress-report.log` |

## 系统要求

- Linux 系统（支持 systemd）
- `tmux` - 用于会话管理
- `notify-send` - 用于桌面通知
- `pi` 命令行工具
- 已配置好的 provider (zai/deepseek)

### 安装依赖（Debian/Ubuntu）

```bash
sudo apt update
sudo apt install tmux libnotify-bin
```

## 手动安装

如果不想使用安装脚本，可以手动安装：

### 1. 复制服务文件

```bash
mkdir -p ~/.config/systemd/user
cp systemd/aifanyi-*.service ~/.config/systemd/user/
cp systemd/aifanyi-*.timer ~/.config/systemd/user/
```

### 2. 重新加载 systemd

```bash
systemctl --user daemon-reload
```

### 3. 启用并启动服务

```bash
# 主驱动
systemctl --user enable --now aifanyi-driver.service

# 看门狗
systemctl --user enable --now aifanyi-watchdog.timer

# 进度汇报
systemctl --user enable --now aifanyi-progress-report.timer
```

## 验证安装

```bash
# 检查服务状态
systemctl --user status aifanyi-driver.service

# 查看定时器
systemctl --user list-timers aifanyi*

# 查看日志
tail -f .claude/pi-driver.log

# 测试通知
notify-send --app-name="AI-FanYi" "测试" "通知功能正常"
```

## 常用命令

### 服务管理

```bash
# 查看服务状态
systemctl --user status aifanyi-driver.service

# 停止服务
systemctl --user stop aifanyi-driver.service

# 启动服务
systemctl --user start aifanyi-driver.service

# 重启服务
systemctl --user restart aifanyi-driver.service

# 查看服务日志
journalctl --user -u aifanyi-driver.service -f
```

### 定时器管理

```bash
# 查看定时器状态
systemctl --user list-timers aifanyi*

# 停止定时器
systemctl --user stop aifanyi-progress-report.timer

# 启动定时器
systemctl --user start aifanyi-progress-report.timer

# 修改定时器（编辑后重新加载）
nano ~/.config/systemd/user/aifanyi-progress-report.timer
systemctl --user daemon-reload
systemctl --user restart aifanyi-progress-report.timer
```

### 进度汇报

```bash
# 手动触发汇报
./scripts/progress-report.sh

# 查看汇报历史
./scripts/view-reports.sh

# 查看汇报日志
tail -f .claude/progress-report.log
```

### 查看日志

```bash
# 驱动日志（实时）
tail -f .claude/pi-driver.log

# 汇报日志（实时）
tail -f .claude/progress-report.log

# 服务日志
journalctl --user -u aifanyi-driver.service -f

# 查看最近的错误
journalctl --user -u aifanyi-driver.service --since "1 hour ago" | grep -i error
```

## 卸载

```bash
# 运行卸载脚本
./scripts/uninstall-unattended.sh
```

或手动卸载：

```bash
# 停止并禁用服务
systemctl --user stop aifanyi-driver.service
systemctl --user stop aifanyi-watchdog.timer
systemctl --user stop aifanyi-progress-report.timer
systemctl --user disable aifanyi-driver.service
systemctl --user disable aifanyi-watchdog.timer
systemctl --user disable aifanyi-progress-report.timer

# 删除服务文件
rm ~/.config/systemd/user/aifanyi-*.service
rm ~/.config/systemd/user/aifanyi-*.timer

# 重新加载 systemd
systemctl --user daemon-reload

# 清理锁文件
rm -f /tmp/aifanyi-driver.lock
```

## 故障排除

### 问题1：服务启动失败

```bash
# 查看详细错误
journalctl --user -u aifanyi-driver.service -n 50

# 检查脚本权限
ls -l scripts/pi-unattended.sh
chmod +x scripts/pi-unattended.sh

# 检查锁文件
ls -la /tmp/aifanyi-driver.lock
rm -f /tmp/aifanyi-driver.lock
```

### 问题2：通知没有显示

```bash
# 测试通知
notify-send --app-name="Test" "测试" "你能看到这条消息吗？"

# 检查通知守护进程
ps aux | grep -E "(dunst|xfce4-notifyd|notification-daemon)"

# 安装通知守护进程（如果需要）
sudo apt install dunst
```

### 问题3：定时器没有触发

```bash
# 查看定时器状态
systemctl --user status aifanyi-progress-report.timer

# 查看下次触发时间
systemctl --user list-timers aifanyi*

# 手动触发测试
systemctl --user start aifanyi-progress-report.service

# 查看服务日志
journalctl --user -u aifanyi-progress-report.service -n 20
```

### 问题4：权限问题

```bash
# 确保脚本有执行权限
chmod +x scripts/*.sh

# 确保服务文件有正确权限
ls -l ~/.config/systemd/user/aifanyi-*

# 如果需要，重新复制
cp systemd/aifanyi-*.service ~/.config/systemd/user/
cp systemd/aifanyi-*.timer ~/.config/systemd/user/
systemctl --user daemon-reload
```

## 自定义配置

### 修改汇报间隔

编辑 `~/.config/systemd/user/aifanyi-progress-report.timer`：

```ini
# 每 15 分钟
OnCalendar=*:0/15

# 每 1 小时
OnCalendar=*:0/60

# 特定时间（每天 9:00, 13:00, 17:00, 21:00）
OnCalendar=09:00,13:00,17:00,21:00
```

然后重新加载：

```bash
systemctl --user daemon-reload
systemctl --user restart aifanyi-progress-report.timer
```

### 修改看门狗检查间隔

编辑 `~/.config/systemd/user/aifanyi-watchdog.timer`：

```ini
# 每 5 分钟
OnCalendar=*:0/5

# 每 20 分钟
OnCalendar=*:0/20
```

### 禁用桌面通知

编辑 `scripts/progress-report.sh`，在 `notify-send` 命令前添加 `#`：

```bash
# notify-send \
#     --app-name="AI-FanYi" \
#     ...
```

## 相关文档

- [完整系统说明](UNATTENDED_SYSTEM_COMPLETE.md)
- [通知功能指南](NOTIFICATION_GUIDE.md)
- [快速参考](UNATTENDED_QUICKREF.md)
- [进度汇报快速参考](PROGRESS_REPORT_QUICKREF.md)
