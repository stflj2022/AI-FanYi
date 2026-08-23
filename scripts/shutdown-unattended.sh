#!/bin/bash
# shutdown-unattended.sh — AI-FanYi 无人值守系统一站式停止（幂等）
# 触发场景：
#   1) 驱动发现项目完工（completion-check.sh 通过）
#   2) 看门狗 / 进度汇报发现项目完工
#   3) 用户手动执行
# 效果：停止并禁用 驱动/web-ui驱动/看门狗/进度汇报 全部 timer 与 service，
#       清理残留驱动进程，写停止标记，只发送一次「完工」终报通知。
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MARKER="$PROJECT_DIR/.claude/UNATTENDED_STOPPED"
LOCK="$PROJECT_DIR/.claude/.shutdown.lock"
LOG="$PROJECT_DIR/.claude/shutdown.log"
mkdir -p "$PROJECT_DIR/.claude"

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; echo "$*"; }

# 0) 原子抢锁（TOCTOU 防护）：驱动/看门狗/汇报可能在同一分钟同时发现完工，
#    noclobber 保证只有第一个实例真正执行停止与终报，其余静默退出。
( set -C; : > "$LOCK" ) 2>/dev/null || exit 0

# 幂等：已停止过则静默退出（避免重复通知/重复操作）
if [ -f "$MARKER" ]; then
    exit 0
fi

log "🛑 开始停止无人值守系统（原因: ${1:-项目完工}）"

# 1) 先停两个 timer，防止停止过程中又触发汇报/拉起驱动
for u in aifanyi-progress-report.timer aifanyi-watchdog.timer; do
    if systemctl --user disable --now "$u" >/dev/null 2>&1; then
        log "⏹  $u 已停止并禁用"
    else
        log "⚠️  $u 停止失败或不存在（忽略）"
    fi
done

# 2) 禁用 driver 与 web-ui-driver（取消开机自启）
systemctl --user disable aifanyi-driver.service >/dev/null 2>&1 || true
systemctl --user disable web-ui-driver.service >/dev/null 2>&1 || true

# 3) 写停止标记（此后驱动/看门狗/汇报见到此文件都会静默退出）
date '+%F %T %Z' > "$MARKER"

# 4) 判断本脚本是否运行在某个受管服务的 cgroup 内（或是其直接子进程）：
#    - 在内部（驱动自停）：不能 stop 自身所在服务（cgroup 清理会连本脚本一起杀），
#      也无需杀调用方——调用方在本脚本返回后立即 exit 0；
#      注：SIGTERM 属 systemd 的干净信号，即使杀了调用方，Restart=on-failure
#      也不会拉起，但杀正在运行本脚本的父进程没有意义，故跳过。
#    - 在外部（汇报/看门狗/手动）：直接 stop 对应服务。
cgroup_of() { systemctl --user show -p ControlGroup --value "$1" 2>/dev/null || true; }
inside_cgroup() { [ -n "$1" ] && grep -qs "$1" /proc/self/cgroup; }
PARENT_CMD="$(tr '\0' ' ' < "/proc/$PPID/cmdline" 2>/dev/null || true)"

INSIDE_DRIVER=0
if inside_cgroup "$(cgroup_of aifanyi-driver.service)" || [[ "$PARENT_CMD" == *pi-unattended.sh* ]]; then
    INSIDE_DRIVER=1
fi
INSIDE_WEBUI=0
if inside_cgroup "$(cgroup_of web-ui-driver.service)" || [[ "$PARENT_CMD" == *web-ui-driver.sh* ]]; then
    INSIDE_WEBUI=1
fi

# 5) 停止 aifanyi-driver.service
if [ "$INSIDE_DRIVER" = "1" ]; then
    log "ℹ️  在 aifanyi 驱动内部调用，驱动将自行 exit 0（Restart=on-failure 不会拉起）"
else
    if systemctl --user stop aifanyi-driver.service >/dev/null 2>&1; then
        log "⏹  aifanyi-driver.service 已停止"
    else
        pkill -f "scripts/pi-unattended[.]sh" 2>/dev/null || true
        log "⏹  aifanyi-driver.service 未运行或已停止（兜底清理进程）"
    fi
fi

# 6) 停止 web-ui-driver.service（该单元若为 Restart=always，只杀进程会无限复活，
#    必须 stop+disable；单元文件本身也应配置 Restart=on-failure）
if [ "$INSIDE_WEBUI" = "1" ]; then
    log "ℹ️  在 web-ui 驱动内部调用，驱动将自行 exit 0（Restart=on-failure 不会拉起）"
else
    if systemctl --user stop web-ui-driver.service >/dev/null 2>&1; then
        log "⏹  web-ui-driver.service 已停止"
    else
        pkill -f "scripts/web-ui-driver[.]sh" 2>/dev/null || true
        log "⏹  web-ui-driver.service 未运行或已停止（兜底清理进程）"
    fi
fi

# 7) 只发送一次终报通知（沿用 replace-id=1001 覆盖掉旧的进度汇报）
if command -v notify-send >/dev/null 2>&1; then
    notify-send \
        --app-name="AI-FanYi" \
        --icon="dialog-information" \
        --urgency="normal" \
        --replace-id=1001 \
        --expire-time=0 \
        "🎉 AI-FanYi 项目已完工" \
        "无人值守监控系统已自动停止：驱动、看门狗、每30分钟进度汇报全部关闭。\n如需重新启用：scripts/install-unattended.sh"
fi

log "✅ 无人值守系统已全部停止（驱动 + web-ui 驱动 + 看门狗 + 进度汇报）"
exit 0
