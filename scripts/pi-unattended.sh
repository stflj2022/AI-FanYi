#!/bin/bash
# pi-unattended.sh — AI-FanYi 无人值守驱动 v8
# 策略: 只用 Zai glm-4.7（非高峰时段）+ 额度耗尽等待重置 + 临时 deepseek 开关
#       + 零输出熔断 + 上下文冷启动 + pytest 独立验收 + flock 单例
#       + 每8轮预防性换会话 + 开机自启(systemd) 适配
set -u
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" >/dev/null 2>&1
export PATH="$HOME/.pi/agent/node_modules/.bin:$PATH"

# 实际项目位置（本地：~/桌面/AI-FanYi）
REPO="$HOME/桌面/AI-FanYi"
LOG="$REPO/.claude/pi-driver.log"
mkdir -p "$REPO/.claude"
cd "$REPO" || exit 1

ZAI_KEY=$(python3 -c 'import json,os;print(json.load(open(os.path.expanduser("~/.pi/agent/auth.json")))["zai-coding-cn"]["key"])' 2>/dev/null || true)
DS_KEY=$(python3 -c 'import json,os;print(json.load(open(os.path.expanduser("~/.pi/agent/auth.json")))["deepseek"]["key"])' 2>/dev/null || true)

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

# 单例守卫：文件锁防双开
exec 9>"/tmp/aifanyi-driver.lock" || exit 1
if ! flock -n 9; then
  echo "[$(date '+%F %T')] ❌ 已有驱动实例持锁，本实例退出" >> "$LOG"
  exit 1
fi

MARK_FILE="$REPO/.claude/.round_mark"

tests_pass() { (cd "$REPO" && timeout 900 .venv/bin/python -m pytest src/filmdub/tests/ -q >/dev/null 2>&1); }

done_check() {
  [ "$(tail -1 "$LOG" | tr -d '[:space:]')" = "ALL_DONE" ] || return 1
  if tests_pass; then return 0; fi
  log "❌ 声称完工但 pytest 未通过 → 打回重做"
  touch "$REPO/.claude/FRESH_NEXT"
  return 1
}

round_out() { local m; m=$(cat "$MARK_FILE" 2>/dev/null || echo 0); tail -c +$((m+1)) "$LOG" 2>/dev/null; }
quota_hit() { round_out | grep -qiE "quota|额度|429|rate.?limit|insufficient|exceeded|余额不足|balance|insufficient_user_quota"; }
ctx_hit() { round_out | grep -qiE "context.{0,20}(length|limit|window|overflow)|maximum context|too long|token limit|context_length_exceeded|prompt is too long"; }

# ---- Zai 额度/探活（每5小时重置，探测非200即视为不可用）----
zai_alive() {
  [ -n "$ZAI_KEY" ] || return 1
  local code
  code=$(curl -sS -m 12 -o /dev/null -w "%{http_code}" \
    "https://api.z.ai/api/coding/paas/v4/chat/completions" \
    -H "Authorization: Bearer $ZAI_KEY" -H "Content-Type: application/json" \
    -d '{"model":"glm-4.7","messages":[{"role":"user","content":"ping"}],"max_tokens":1}' 2>/dev/null)
  [ "$code" = "200" ]
}

# ---- 非高峰判断：工作日(周一~五) 14:00-18:00 为高峰，其余为非高峰 ----
is_peak_hour() {
  local dow hour
  dow=$(date +%u)      # 1=Mon ... 7=Sun
  hour=$(date +%H)     # 0-23
  [ "$dow" -ge 1 ] && [ "$dow" -le 5 ] && [ "$hour" -ge 14 ] && [ "$hour" -lt 18 ]
}

# ---- 决定当前 provider ----
# 临时 deepseek 开关：存在 TEMP_DEEPSEEK 标志文件 → 用 deepseek（绕过高峰/额度）
current_provider() {
  if [ -f "$REPO/.claude/TEMP_DEEPSEEK" ]; then
    echo "deepseek/deepseek-v4-flash"
  else
    echo "zai-coding-cn/glm-4.7"
  fi
}

run_pi() {
  local prov="$1" cont_prompt="$2"
  local cont=(-c)
  if [ -f "$REPO/.claude/FRESH_NEXT" ]; then cont=(); rm -f "$REPO/.claude/FRESH_NEXT"; fi
  echo "[$(date '+%F %T')] ▶ pi 启动 ($prov)" >> "$LOG"
  local mark; mark=$(stat -c %s "$LOG")
  echo "$mark" > "$MARK_FILE"
  timeout 7200 pi --provider "${prov%%/*}" --model "${prov##*/}" "${cont[@]}" -p "$cont_prompt" < /dev/null >> "$LOG" 2>&1 &
  local pid=$!
  local zeros=0 last_cpu=""
  while kill -0 "$pid" 2>/dev/null; do
    sleep 30
    local pic; pic=$(pgrep -P "$pid" | head -1)
    local cpu_now=""; [ -n "$pic" ] && cpu_now=$(ps -o cputime= -p "$pic" 2>/dev/null | tr -d ' ')
    local s1; s1=$(stat -c %s "$LOG")
    if [ "$s1" -le "$mark" ]; then
      if [ -n "$cpu_now" ] && [ "$cpu_now" != "$last_cpu" ]; then zeros=0; else zeros=$((zeros+1)); fi
      last_cpu="$cpu_now"
      if [ "$zeros" -ge 30 ]; then
        log "⏳ 零输出熔断（900s 输出与 CPU 双静默）"
        touch "$REPO/.claude/FRESH_NEXT"
        pkill -TERM -P "$pid" 2>/dev/null; kill "$pid" 2>/dev/null
        return
      fi
      continue
    fi
    zeros=0
    sleep 30
    local s2; s2=$(stat -c %s "$LOG")
    if [ "$s2" = "$s1" ] && tail -1 "$LOG" | grep -qE '^400:|exceeds max length'; then
      log "⚡ 报错后挂起，提前终止本轮"
      pkill -TERM -P "$pid" 2>/dev/null; kill "$pid" 2>/dev/null
      return
    fi
    mark=$s2
  done
  wait "$pid" 2>/dev/null
}

safe_push() {
  if [ -n "$(git status --porcelain 2>/dev/null)" ] || git log origin/main..HEAD --oneline 2>/dev/null | grep -q .; then
    git add -A && git commit -m "chore(driver): 自动检查点 $(date '+%F %T')" --allow-empty -q >> "$LOG" 2>&1
    git push -q origin HEAD >> "$LOG" 2>&1 && log "✅ 已推送 GitHub" || log "⚠️ push 失败，下轮重试"
  fi
}

# ---- 主循环 ----
CONT_PROMPT="按 docs/ROADMAP_2MONTH.md（2个月路线图）推进当前阶段。每轮：1) 读 CLAUDE.md/CONTEXT.md 与 specs/、docs/tickets/ 工单状态；2) 取一张未阻塞 todo 工单，用 implement 实现（qwentts 集成 M04/M09/M02/M05 用 adapter 层，勿破坏 M01-M03 已验证行为）；3) 测试命令固定 cd ~/桌面/AI-FanYi && .venv/bin/python -m pytest src/filmdub/tests/ -q，全量绿后 commit(格式 feat(Mxx): 描述)+push；4) 每3张工单用 code-review 检查修复；5) 连续失败3次→工单标 blocked 换下一张；6) 禁止提问等待，自主决策执行。全部工单真正达标后最后一行只输出 ALL_DONE。"

# ---- 首轮 kickoff ----
if [ ! -f "$REPO/.claude/KICKOFF_DONE" ]; then
  log "=== KICKOFF 开始 ==="
  run_pi "$(current_provider)" "$(cat "$REPO/.claude/KICKOFF.md")"
  touch "$REPO/.claude/KICKOFF_DONE"
  log "=== KICKOFF 结束 ==="
fi

N=0
while true; do
  N=$((N+1))

  # 完工自停：全部工单已完成 → 停止驱动/看门狗/汇报，不再空转烧额度
  if "$REPO/scripts/completion-check.sh" >/dev/null 2>&1; then
    log "🎉 项目已完工 → 自动停止无人值守系统"
    "$REPO/scripts/shutdown-unattended.sh" "项目完工（驱动触发）" >> "$LOG" 2>&1 || true
    exit 0
  fi

  # 临时 deepseek 模式下：若 zai 已恢复(非高峰+额度可用)则自动切回
  if [ -f "$REPO/.claude/TEMP_DEEPSEEK" ] && ! is_peak_hour && zai_alive; then
    log "✅ zai 已恢复可用，自动切回（移除临时 deepseek 标志）"
    rm -f "$REPO/.claude/TEMP_DEEPSEEK"
  fi

  # 决定本轮 provider（含非高峰/额度等待）
  CUR=$(current_provider)
  if [ "$CUR" = "zai-coding-cn/glm-4.7" ]; then
    if is_peak_hour; then
      log "⏰ 高峰时段(工作日14-18点)，睡 600s 等待非高峰"
      sleep 600; continue
    fi
    if ! zai_alive; then
      log "💤 zai 额度耗尽/不可用（约5小时重置），睡 900s 等待"
      sleep 900; continue
    fi
  elif [ -n "$DS_KEY" ] && ! curl -sS -m 8 -o /dev/null -w "%{http_code}" "https://api.deepseek.com/chat/completions" -H "Authorization: Bearer $DS_KEY" -H "Content-Type: application/json" -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"ping"}],"max_tokens":1}' 2>/dev/null | grep -q "200"; then
    log "💤 deepseek(临时) 不可用，睡 300s"
    sleep 300; continue
  fi

  if [ $((N % 8)) -eq 0 ]; then
    log "🔄 每8轮预防性换新会话"
    touch "$REPO/.claude/FRESH_NEXT"
  fi

  log "=== ROUND $N ($CUR) ==="
  run_pi "$CUR" "$CONT_PROMPT"
  safe_push
  if done_check; then
    log "🎉 全部工单完成（pytest 验收通过）→ 自动停止无人值守系统"
    safe_push
    "$REPO/scripts/shutdown-unattended.sh" "项目完工（驱动 done_check 触发）" >> "$LOG" 2>&1 || true
    exit 0
  fi

  if ctx_hit; then
    log "⚠️ 会话上下文满 → 开新会话恢复"
    touch "$REPO/.claude/FRESH_NEXT"
    run_pi "$CUR" "$(cat "$REPO/.claude/RECOVERY.md")"
    safe_push
    continue
  fi

  if quota_hit; then
    log "🔁 配额类错误 → 弃旧会话，下轮重新探活等待"
    touch "$REPO/.claude/FRESH_NEXT"
    sleep 120
    continue
  fi

  log "一轮正常结束，30s 后继续下一轮"
  sleep 30
done
