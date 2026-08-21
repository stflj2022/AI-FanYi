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

CONT_PROMPT="阶段2-深度化复验。上一阶段产出的实现多为骨架，不算完成。逐张处理 docs/tickets/ 工单：1) 审查现有代码，补齐真实业务逻辑（禁止空壳/TODO/假数据充数）；2) 为核心功能编写有意义的 pytest 测试；3) 运行 pytest 全部通过后，才能把工单标为 done 并 commit+push；4) 测试不过就继续修，不许降低标准。禁止提问等待确认，自主决策直接执行。所有工单都真正达标后，最后一行只输出 ALL_DONE。"

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

# 单例守卫：文件锁防双开（pgrep 会误匹配 tmux 包装 shell）
exec 9>"/tmp/aifanyi-driver.lock" || exit 1
if ! flock -n 9; then
  echo "[$(date '+%F %T')] ❌ 已有驱动实例持锁，本实例退出" >> "$LOG"
  exit 1
fi

done_check() { [ "$(tail -1 "$LOG" | tr -d '[:space:]')" = "ALL_DONE" ]; }
quota_hit() { tail -80 "$LOG" | grep -qiE "quota|额度|429|rate.?limit|insufficient|exceeded|余额不足|balance"; }

run_pi() {
  local cont=(-c)
  if [ -f "$REPO/.claude/FRESH_NEXT" ]; then cont=(); rm -f "$REPO/.claude/FRESH_NEXT"; fi
  echo "[$(date '+%F %T')] ▶ pi 启动" >> "$LOG"
  local mark; mark=$(stat -c %s "$LOG")
  timeout 7200 pi --provider "$1" --model "$2" "${cont[@]}" -p "$3" < /dev/null >> "$LOG" 2>&1 &
  local pid=$!
  while kill -0 "$pid" 2>/dev/null; do
    sleep 30
    local s1; s1=$(stat -c %s "$LOG")
    [ "$s1" -le "$mark" ] && continue
    sleep 30
    local s2; s2=$(stat -c %s "$LOG")
    if [ "$s2" = "$s1" ] && tail -1 "$LOG" | grep -qE '^400:|exceeds max length'; then
      log "⚡ 报错后挂起，提前终止本轮"
      pkill -TERM -P "$pid" 2>/dev/null
      kill "$pid" 2>/dev/null
      return
    fi
    mark=$s2
  done
  wait "$pid" 2>/dev/null
}

ctx_hit() { tail -30 "$LOG" | grep -qiE "context.{0,20}(length|limit|window|overflow)|maximum context|too long|token limit|context_length_exceeded|prompt is too long|exceeds max length"; }

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
    run_pi "$P_PROVIDER" "$P_MODEL" "$(cat "$REPO/.claude/RECOVERY.md")

$CONT_PROMPT"
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
