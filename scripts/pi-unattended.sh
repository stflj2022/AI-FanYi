#!/bin/bash
# pi-unattended.sh — AI-FanYi 无人值守驱动 v7
# 策略: provider 轮换（zai glm-4.7 ↔ deepseek v4-pro）+ 零输出熔断 + 上下文冷启动
#       + pytest 独立验收 + flock 单例 + 每8轮预防性换会话 + cron 看门狗兜底
set -u
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" >/dev/null 2>&1
export PATH="$HOME/.pi/agent/node_modules/.bin:$PATH"

REPO="$HOME/AI-FanYi"
LOG="$REPO/.claude/pi-driver.log"
mkdir -p "$REPO/.claude"
cd "$REPO" || exit 1

PROVIDERS=("zai-coding-cn/glm-4.7" "deepseek/deepseek-v4-pro")
PI=0
FAILS=0
ZAI_KEY=$(python3 -c 'import json,os;print(json.load(open(os.path.expanduser("~/.pi/agent/auth.json")))["zai-coding-cn"]["key"])' 2>/dev/null || true)
DS_KEY=$(python3 -c 'import json,os;print(json.load(open(os.path.expanduser("~/.pi/agent/auth.json")))["deepseek"]["key"])' 2>/dev/null || true)

CONT_PROMPT="阶段2-深度化复验（第3轮）。前两轮均虚报完工被驱动打回：测试套件实际处于损坏状态。本轮规则：1) 测试命令固定为 cd ~/AI-FanYi && .venv/bin/python -m pytest src/filmdub/tests/ -q，先修复全部收集错误（已知问题：test_media_intake/test_research/test_subtitle 的 import 路径断链，No module named 'core'/'workers'）；2) 全量测试绿了之后，逐张审查 docs/tickets/ 工单，补齐真实业务逻辑（禁止空壳/TODO/假数据），新功能必须配测试；3) 每完成一张工单：跑全量测试→绿→标done→commit；4) 驱动会独立复跑 pytest 验证，测试不过的 ALL_DONE 会被打回，虚报无效；5) 禁止提问等待确认，自主决策直接执行。所有工单真正达标后，最后一行只输出 ALL_DONE。"

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

# 单例守卫：文件锁防双开（pgrep 会误匹配 tmux 包装 shell）
exec 9>"/tmp/aifanyi-driver.lock" || exit 1
if ! flock -n 9; then
  echo "[$(date '+%F %T')] ❌ 已有驱动实例持锁，本实例退出" >> "$LOG"
  exit 1
fi

cur() { echo "${PROVIDERS[$PI]}"; }

MARK_FILE="$REPO/.claude/.round_mark"

tests_pass() { (cd "$REPO" && timeout 600 .venv/bin/python -m pytest src/filmdub/tests/ -q >/dev/null 2>&1); }

done_check() {
  [ "$(tail -1 "$LOG" | tr -d '[:space:]')" = "ALL_DONE" ] || return 1
  if tests_pass; then return 0; fi
  log "❌ 声称完工但 pytest 未通过 → 打回重做"
  touch "$REPO/.claude/FRESH_NEXT"
  return 1
}

# 只检查本轮新增输出，避免匹配到日志里的历史错误（tail -c +N 从 N 字节起）
round_out() { local m; m=$(cat "$MARK_FILE" 2>/dev/null || echo 0); tail -c +$((m+1)) "$LOG" 2>/dev/null; }

quota_hit() { round_out | grep -qiE "quota|额度|429|rate.?limit|insufficient|exceeded|余额不足|balance"; }

ctx_hit() { round_out | grep -qiE "context.{0,20}(length|limit|window|overflow)|maximum context|too long|token limit|context_length_exceeded|prompt is too long|exceeds max length"; }

zai_alive() {
  [ -n "$ZAI_KEY" ] || return 1
  local code
  code=$(curl -sS -m 10 -o /dev/null -w "%{http_code}" \
    "https://api.z.ai/api/coding/paas/v4/chat/completions" \
    -H "Authorization: Bearer $ZAI_KEY" -H "Content-Type: application/json" \
    -d '{"model":"glm-4.7","messages":[{"role":"user","content":"ping"}],"max_tokens":1}' 2>/dev/null)
  [ "$code" = "200" ]
}

deepseek_alive() {
  [ -n "$DS_KEY" ] || return 1
  local code
  code=$(curl -sS -m 10 -o /dev/null -w "%{http_code}" \
    "https://api.deepseek.com/chat/completions" \
    -H "Authorization: Bearer $DS_KEY" -H "Content-Type: application/json" \
    -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"ping"}],"max_tokens":1}' 2>/dev/null)
  [ "$code" = "200" ]
}

provider_alive() {
  case "${PROVIDERS[$PI]%%/*}" in
    zai-coding-cn) zai_alive ;;
    deepseek)      deepseek_alive ;;
    *) return 1 ;;
  esac
}

primary_alive() { [ "$PI" -ne 0 ] && zai_alive; }

run_pi() {
  local cont=(-c)
  if [ -f "$REPO/.claude/FRESH_NEXT" ]; then cont=(); rm -f "$REPO/.claude/FRESH_NEXT"; fi
  echo "[$(date '+%F %T')] ▶ pi 启动" >> "$LOG"
  local mark; mark=$(stat -c %s "$LOG")
  echo "$mark" > "$MARK_FILE"
  timeout 7200 pi --provider "${1%%/*}" --model "${1##*/}" "${cont[@]}" -p "$2" < /dev/null >> "$LOG" 2>&1 &
  local pid=$!
  local zeros=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 30
    local s1; s1=$(stat -c %s "$LOG")
    if [ "$s1" -le "$mark" ]; then
      zeros=$((zeros+1))
if [ "$zeros" -ge 30 ]; then
log "⏳ 零输出熔断（900s 无任何响应）"
        touch "$REPO/.claude/ROTATE_NEXT"
        pkill -TERM -P "$pid" 2>/dev/null
        kill "$pid" 2>/dev/null
        return
      fi
      continue
    fi
    zeros=0
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

safe_push() {
  if [ -n "$(git status --porcelain 2>/dev/null)" ] || git log origin/main..HEAD --oneline 2>/dev/null | grep -q .; then
    git add -A && git commit -m "chore(driver): 自动检查点 $(date '+%F %T')" --allow-empty -q >> "$LOG" 2>&1
    git push -q origin HEAD >> "$LOG" 2>&1 && log "✅ 已推送 GitHub" || log "⚠️ push 失败，下轮重试"
  fi
}

# ---- 首轮 kickoff ----
if [ ! -f "$REPO/.claude/KICKOFF_DONE" ]; then
  log "=== KICKOFF 开始 ($(cur)) ==="
  run_pi "$(cur)" "$(cat "$REPO/.claude/KICKOFF.md")"
  touch "$REPO/.claude/KICKOFF_DONE"
  log "=== KICKOFF 结束 ==="
fi

# ---- 启动探测：主力不可用直接从备用起步 ----
if ! zai_alive; then
  PI=1
  log "🚀 启动探测：zai 不可用，从 $(cur) 起步"
fi

# ---- 主循环 ----
N=0
while true; do
  N=$((N+1))

  # 备用运行期间探测主力，恢复即切回（省 deepseek 按量费用）
  if [ "$PI" -ne 0 ] && primary_alive; then
    log "✅ 主力 zai 恢复可用，切回"
    PI=0; FAILS=0
  fi

  if [ $((N % 8)) -eq 0 ]; then
    log "🔄 每8轮预防性换新会话（防上下文膨胀）"
    touch "$REPO/.claude/FRESH_NEXT"
  fi

  log "=== ROUND $(cur) ==="
  run_pi "$(cur)" "$CONT_PROMPT"
  safe_push
  if done_check; then log "🎉 全部工单完成（pytest 验收通过）"; safe_push; break; fi

  # 上下文满 → 同 provider 冷启动恢复（状态在 specs/tickets/git，无损）
  if ctx_hit; then
    log "⚠️ 会话上下文满 → 开新会话"
    touch "$REPO/.claude/FRESH_NEXT"
    run_pi "$(cur)" "$(cat "$REPO/.claude/RECOVERY.md")

$CONT_PROMPT"
    safe_push
    continue
  fi

  # provider 故障（配额尽 / 零输出熔断）→ 轮换下家并强制新会话（爆胀会话会拖死好 provider）
  # 全员阵亡则睡等重置
  if [ -f "$REPO/.claude/ROTATE_NEXT" ]; then
    rm -f "$REPO/.claude/ROTATE_NEXT"
    # 分诊：provider 活着说明是慢轮次/会话问题，留家换新会话；死了才轮换
    if provider_alive; then
      log "🩺 $(cur) 探活通过但轮次无输出 → 留家换新会话"
      touch "$REPO/.claude/FRESH_NEXT"
      FAILS=0
      continue
    fi
    FAILS=$((FAILS+1))
    log "🔁 当前 provider 无响应 → 轮换（弃旧会话）"
    touch "$REPO/.claude/FRESH_NEXT"
    PI=$(( (PI+1) % ${#PROVIDERS[@]} ))
    if [ "$FAILS" -ge ${#PROVIDERS[@]} ]; then
      log "💤 全部 provider 不可用，睡 900s 后重试"
      sleep 900
      FAILS=0
    fi
    continue
  fi
  if quota_hit; then
    FAILS=$((FAILS+1))
    log "🔁 配额类错误 → 轮换（弃旧会话）"
    touch "$REPO/.claude/FRESH_NEXT"
    PI=$(( (PI+1) % ${#PROVIDERS[@]} ))
    if [ "$FAILS" -ge ${#PROVIDERS[@]} ]; then
      log "💤 全部 provider 不可用，睡 900s 后重试"
      sleep 900
      FAILS=0
    fi
    continue
  fi

  FAILS=0
  log "一轮正常结束，30s 后继续下一轮"
  sleep 30
done
