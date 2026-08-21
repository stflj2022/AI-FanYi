#!/bin/bash
# pi-unattended.sh — AI-FanYi 无人值守驱动
# 策略: zai(glm-4.7) 主力 → 额度尽切 deepseek-v4-pro → 双尽则每10分钟轮询等 zai 5h 重置
set -u
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" >/dev/null 2>&1
export PATH="$HOME/.pi/agent/node_modules/.bin:$PATH"

REPO="$HOME/AI-FanYi"
LOG="$REPO/.claude/pi-driver.log"
mkdir -p "$REPO/.claude"
cd "$REPO" || exit 1

P_PROVIDER="zai-coding-cn"; P_MODEL="glm-4.7"
F_PROVIDER="deepseek";      F_MODEL="deepseek-v4-pro"

CONT_PROMPT="继续推进。读 docs/tickets/ 下工单状态，挑一个未阻塞的 todo 工单立即实施；完成→测试→git commit→更新工单状态。若上一轮有未完成工作先接着做。禁止向用户提问或等待确认，一切自主决策直接执行。全部工单完成后只输出 ALL_DONE。"

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }
done_check() { tail -100 "$LOG" | grep -q "ALL_DONE"; }
quota_hit() { tail -80 "$LOG" | grep -qiE "quota|额度|429|rate.?limit|insufficient|exceeded|余额不足|balance"; }

run_pi() {
  local cont=(-c)
  if [ -f "$REPO/.claude/FRESH_NEXT" ]; then cont=(); rm -f "$REPO/.claude/FRESH_NEXT"; fi
  timeout 7200 pi --provider "$1" --model "$2" "${cont[@]}" -p "$3" < /dev/null >> "$LOG" 2>&1
}

ctx_hit() { tail -30 "$LOG" | grep -qiE "context.{0,20}(length|limit|window|overflow)|maximum context|too long|token limit|context_length_exceeded|prompt is too long"; }

safe_push() {
  if [ -n "$(git status --porcelain 2>/dev/null)" ] || git log origin/main..HEAD --oneline 2>/dev/null | grep -q .; then
    git add -A && git commit -m "chore(driver): 自动检查点 $(date '+%F %T')" --allow-empty -q >> "$LOG" 2>&1
    git push -q origin HEAD >> "$LOG" 2>&1 && log "✅ 已推送 GitHub" || log "⚠️ push 失败，下轮重试"
  fi
}

# ---- 首轮 kickoff ----
if [ ! -f "$REPO/.claude/KICKOFF_DONE" ]; then
  log "=== KICKOFF 开始 ($P_PROVIDER/$P_MODEL) ==="
  run_pi "$P_PROVIDER" "$P_MODEL" "$(cat "$REPO/.claude/KICKOFF.md")"
  touch "$REPO/.claude/KICKOFF_DONE"
  log "=== KICKOFF 结束 ==="
fi

# ---- 主循环 ----
while true; do
  log "=== ROUND $P_PROVIDER/$P_MODEL ==="
  run_pi "$P_PROVIDER" "$P_MODEL" "$CONT_PROMPT"
  safe_push
  done_check && { log "🎉 全部工单完成"; safe_push; break; }

  # 上下文满 → 弃旧会话，冷启动新会话从磁盘状态恢复
  if ctx_hit; then
    log "⚠️ 会话上下文满 → 开新会话（状态在 specs/tickets/git，无损）"
    touch "$REPO/.claude/FRESH_NEXT"
    run_pi "$P_PROVIDER" "$P_MODEL" "$(cat "$REPO/.claude/RECOVERY.md")"
    safe_push
    continue
  fi

  if quota_hit; then
    log "zai 额度尽 → 切 $F_PROVIDER/$F_MODEL"
    run_pi "$F_PROVIDER" "$F_MODEL" "$CONT_PROMPT"
    safe_push
    done_check && { log "🎉 全部工单完成"; safe_push; break; }
    if quota_hit; then
      log "双 provider 额度尽 → 睡 600s 等 zai 5h 重置"
      sleep 600
    fi
    continue
  fi

  log "一轮正常结束，30s 后继续下一轮"
  sleep 30
done
