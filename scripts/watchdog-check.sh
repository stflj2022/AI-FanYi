#!/bin/bash
# watchdog-check.sh — 由 systemd aifanyi-watchdog.timer 定期调用（每10分钟）
# 职责：驱动存活检查（按启用状态分别守护 aifanyi 主线驱动与 web-ui 驱动）；
#       项目完工时负责触发一站式自停（而不是继续拉起驱动）。

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_DIR/.claude/watchdog.log"

log() { echo "[$(date '+%F %T')] $*" >> "$LOG_FILE"; }

# 1) 系统已停止（完工自停或手动停止）→ 永不干预、永不拉起
if [ -f "$PROJECT_DIR/.claude/UNATTENDED_STOPPED" ]; then
    exit 0
fi

# 2) 项目已完工 → 触发一站式停止（驱动+看门狗+进度汇报全部关闭），不再拉起驱动
if "$SCRIPT_DIR/completion-check.sh" >/dev/null 2>&1; then
    log "🎉 项目已完工 → 自动停止无人值守系统"
    "$SCRIPT_DIR/shutdown-unattended.sh" "项目完工（看门狗触发）" || true
    exit 0
fi

# 3) 驱动进程存活检查 → 仅对「已启用」的服务兜底，禁用的服务绝不拉起
unit_enabled() { [ "$(systemctl --user is-enabled "$1" 2>/dev/null)" = "enabled" ]; }

if unit_enabled aifanyi-driver.service && ! pgrep -f "pi-unattended[.]sh" >/dev/null 2>&1; then
    log "aifanyi-driver 未运行，尝试重启..."
    systemctl --user restart aifanyi-driver.service
    log "重启命令已发送"
fi

if unit_enabled web-ui-driver.service && ! pgrep -f "web-ui-driver[.]sh" >/dev/null 2>&1; then
    log "web-ui-driver 未运行，尝试重启..."
    systemctl --user restart web-ui-driver.service
    log "重启命令已发送"
fi

exit 0
