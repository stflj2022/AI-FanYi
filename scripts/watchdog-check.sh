#!/bin/bash
# AI-FanYi Watchdog 检查脚本
# 检查 driver 是否运行，如果未运行则重启

set -e

# 检查 pi-unattended.sh 进程是否存在
if ! pgrep -f "pi-unattended.sh" >/dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Watchdog: Driver 未运行，尝试重启..." >> "$PROJECT_ROOT/.claude/watchdog.log"
    systemctl --user restart aifanyi-driver.service
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Watchdog: 重启命令已发送" >> "$PROJECT_ROOT/.claude/watchdog.log"
fi
