#!/bin/bash
# watchdog.sh — cron 每10分钟调用：检查无人值守驱动存活状态，挂了自动拉起
REPO="$HOME/AI-FanYi"
LOG="$REPO/.claude/watchdog.log"
DRV_LOG="$REPO/.claude/pi-driver.log"
SCRIPT="$REPO/scripts/pi-unattended.sh"

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

# 1) 已全部完成 → 不再干预
if [ -f "$DRV_LOG" ] && tail -50 "$DRV_LOG" | grep -q "ALL_DONE"; then
  exit 0
fi

# 2) 驱动进程存活检查
if pgrep -f "scripts/pi-unattended[.]sh" >/dev/null; then
  # 卡死检测：日志 60 分钟无更新 → 杀掉挂起的 pi 轮次，让驱动自动进下一轮
  if [ -f "$DRV_LOG" ]; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$DRV_LOG") ))
    if [ $AGE -gt 3600 ]; then
      PIPID=$(pgrep -f "^timeout 7200 pi" | head -1)
      if [ -n "$PIPID" ]; then
        log "🚨 日志 $((AGE/60)) 分钟无更新且 pi 挂起 → 杀掉卡死轮次"
        pkill -P "$PIPID" 2>/dev/null
        kill "$PIPID" 2>/dev/null
      fi
    fi
  fi
  exit 0
fi

# 3) 死了 → 自动重启（KICKOFF_DONE 已存在会跳过开工阶段，从工单断点续跑）
log "🚨 驱动未在运行 → 自动重启"
tmux kill-session -t aifanyi 2>/dev/null
tmux new-session -d -s aifanyi "$SCRIPT"
if [ $? -eq 0 ]; then log "✅ 重启成功"; else log "❌ 重启失败"; fi
