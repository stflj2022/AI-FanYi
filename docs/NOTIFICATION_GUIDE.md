# AI-FanYi 桌面通知说明

## 通知行为

### ✅ 核心特性

1. **停留在桌面**
   - 通知不会自动消失
   - 需要手动点击才能关闭

2. **自动替换**
   - 多次通报时，只保留**最近的一次**
   - 旧的通知会被新通知自动替换
   - 避免通知堆积

3. **智能图标**
   - 🟢 **运行中**：蓝色信息图标
   - 🔴 **未运行**：红色错误图标

---

## 通知内容

```
📋 AI-FanYi 进度汇报 [时间]
📊 Driver: ✅ 运行中 | Watchdog: ✅ 正常
🤖 Unattended: ✅ 正常
🔀 最新提交
🎫 工单进度 (完成/总数)
💻 系统资源 (CPU | 内存)
```

### 说明

- **Driver**: aifanyi-driver.service 的运行状态（主驱动服务）
- **Watchdog**: aifanyi-watchdog.service 的运行状态（监控服务）
- **Unattended**: unattended-dev-system 综合状态
  - ✅ 正常：所有服务正常运行
  - ⚠️ 部分：watchdog 异常
  - ❌ 异常：driver 未运行

---

## 汇报时间

- **频率**：每 30 分钟
- **时间点**：整点和半点（00:00, 00:30, 01:00, ...）

---

## 测试通知

```bash
# 发送测试通知
notify-send --app-name="AI-FanYi-Test" --icon="dialog-information" --urgency="normal" --replace-id=1001 --expire-time=0 "测试" "通知功能正常"
```

---

## 手动触发汇报

```bash
# 立即生成一次汇报并发送通知
~/桌面/AI-FanYi/scripts/progress-report.sh
```

---

## 修改通知行为

### 恢复自动消失

编辑脚本：
```bash
nano ~/桌面/AI-FanYi/scripts/progress-report.sh
```

找到这行：
```bash
--expire-time=0 \
```

改为（10 秒后自动消失）：
```bash
--expire-time=10000 \
```

### 修改替换行为

如果要保留所有通知（不替换），删除或注释这行：
```bash
# --replace-id=1001 \
```

---

## 禁用通知

如果不需要通知，可以注释掉整个通知发送部分：

```bash
nano ~/桌面/AI-FanYi/scripts/progress-report.sh

# 在 notify-send 命令前添加 # 即可
# notify-send \
#     --app-name="AI-FanYi" \
#     ...
```

---

## 查看通知历史

### GNOME 桌面

```bash
# 查看通知中心
gapplication org.gnome.Shell.Notifications
```

或者按 `Super + A` 打开活动视图，然后点击右上角的通知图标。

### 其他桌面环境

- **KDE**：点击系统托盘的通知图标
- **XFCE**：点击面板上的通知图标
- **使用 dunst**：通知历史需要配置 dunst 的历史功能

---

## 故障排查

### 通知没有显示

1. **检查桌面通知设置**
   - GNOME：设置 → 通知
   - KDE：系统设置 → 通知
   - XFCE：设置 → 通知

2. **检查通知守护进程**
   ```bash
   ps aux | grep -E "(dunst|xfce4-notifyd|notification-daemon|mako)"
   ```

3. **手动测试**
   ```bash
   notify-send "测试" "如果看不到这条通知，说明通知功能有问题"
   ```

### 通知被替换太快

这是因为使用了 `--replace-id=1001`，所有相同 ID 的通知会互相替换。

如果想保留所有通知的历史，可以：
1. 删除 `--replace-id=1001` 这行
2. 或者每次使用不同的 ID（但这样通知会堆积）

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `~/桌面/AI-FanYi/scripts/progress-report.sh` | 汇报脚本（包含通知发送代码） |
| `~/桌面/AI-FanYi/.claude/progress-report.log` | 汇报日志（完整记录） |
| `~/.config/systemd/user/aifanyi-progress-report.timer` | 定时器配置 |
