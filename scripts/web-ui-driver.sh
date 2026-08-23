#!/bin/bash
# pi-web-ui-driver.sh — AI-FanYi Web UI 无人值守驱动
# 监控 Web UI 14 个 tickets 的完成情况
set -u

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" >/dev/null 2>&1
export PATH="$HOME/.pi/agent/node_modules/.bin:$PATH"

# 实际项目位置
REPO="$HOME/桌面/AI-FanYi"
LOG="$REPO/.claude/web-ui-driver.log"
mkdir -p "$REPO/.claude"
cd "$REPO" || exit 1

ZAI_KEY=$(python3 -c 'import json,os;print(json.load(open(os.path.expanduser("~/.pi/agent/auth.json")))["zai-coding-cn"]["key"])' 2>/dev/null || true)

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

# 单例守卫：文件锁防双开
exec 9>"/tmp/web-ui-driver.lock" || exit 1
if ! flock -n 9; then
  echo "[$(date '+%F %T')] ❌ 已有驱动实例持锁，本实例退出" >> "$LOG"
  exit 1
fi

# Web UI 完工标记（由 all_tickets_done 分支在测试通过后写入；done_check 依据它退出）
WEBUI_DONE_MARK="$REPO/.claude/.webui_all_done"
rm -f "$WEBUI_DONE_MARK"   # 启动时清理旧标记，避免历史 ALL_DONE 导致一启动就误判完工

# Web UI 测试
web_ui_tests_pass() {
  # 后端测试
  if ! (cd "$REPO" && timeout 300 .venv/bin/python -m pytest src/filmdub/apps/web/backend/tests/ -q >/dev/null 2>&1); then
    return 1
  fi
  # 前端测试（基础）
  if ! (cd "$REPO/src/filmdub/apps/web/frontend" && npx vitest run simple.test.ts >/dev/null 2>&1); then
    return 1
  fi
  return 0
}

done_check() {
  [ -f "$WEBUI_DONE_MARK" ] || return 1
  if web_ui_tests_pass; then return 0; fi
  log "❌ 声称完工但测试未通过 → 打回重做"
  rm -f "$WEBUI_DONE_MARK"
  touch "$REPO/.claude/WEB_UI_FRESH_NEXT"
  return 1
}

# ---- Zai 额度/探活（每5小时重置）----
zai_alive() {
  [ -n "$ZAI_KEY" ] || return 1
  local code
  code=$(curl -sS -m 12 -o /dev/null -w "%{http_code}" \
    "https://api.z.ai/api/coding/paas/v4/chat/completions" \
    -H "Authorization: Bearer $ZAI_KEY" \
    -H "Content-Type: application/json" \
    -d '{"model":"glm-4.7","messages":[{"role":"user","content":"ping"}],"max_tokens":1}' 2>/dev/null)
  [ "$code" = "200" ] || [ "$code" = "401" ]
}

# ---- 检查所有 tickets 是否完成 ----
all_tickets_done() {
  local tickets_dir="$REPO/.scratch/web-ui-tickets"
  local readme="$tickets_dir/README.md"

  if [ ! -f "$readme" ]; then
    return 1
  fi

  # 检查 README 中的进度跟踪
  if grep -q "✓" "$readme" && ! grep -q "^\- \[ \]" "$readme"; then
    return 0
  fi

  return 1
}

update_tickets_progress() {
  local tickets_dir="$REPO/.scratch/web-ui-tickets"
  local readme="$tickets_dir/README.md"
  local ticket ticket_num summary_file

  # 检查每个 ticket 的完成状态
  for ticket in "$tickets_dir"/[0-9]*-*.md; do
    if [ -f "$ticket" ]; then
      ticket_num=$(basename "$ticket" | cut -d'-' -f1)
      summary_file="$tickets_dir/ticket-$ticket_num-summary.md"
      if [ -f "$summary_file" ]; then
        # Ticket 已完成（锚定连字符，避免把 1 误匹配 10~19）
        sed -i "s/^- \[ \] $ticket_num-/✓ $ticket_num-/" "$readme" 2>/dev/null || true
      fi
    fi
  done
}

# ---- 主循环 ----
ROUND=0
while true; do
  # 完工自停：整个项目（docs/tickets）已完工 → 停止全部监控与通知
  if "$REPO/scripts/completion-check.sh" >/dev/null 2>&1; then
    log "🎉 项目已完工 → 自动停止无人值守系统"
    "$REPO/scripts/shutdown-unattended.sh" "项目完工（web-ui 驱动触发）" >> "$LOG" 2>&1 || true
    exit 0
  fi

  # 检查是否全部完成（必须在本轮写入 ROUND 标记之前判断，否则 tail -1 恒为 ROUND 行，永远不命中）
  if done_check; then
    log "🎉 全部完成，退出驱动"
    break
  fi

  ROUND=$((ROUND + 1))
  log "=== ROUND $ROUND ==="

  # 更新 tickets 进度
  update_tickets_progress

  # 检查所有 tickets 是否完成
  if all_tickets_done; then
    log "🎉 所有 tickets 已完成"

    # 最终验证
    if web_ui_tests_pass; then
      log "✅ 最终测试通过"
      # 提交最后的状态
      git add -A
      git commit -m "chore(web-ui): 完成 Web UI 全部 tickets" || true
      git push origin main || true
      # 写入完工标记，下轮 done_check 命中后退出驱动（不再依赖会被日志行淹没的 tail -1 ALL_DONE）
      touch "$WEBUI_DONE_MARK"
      echo "ALL_DONE" >> "$LOG"
      log "🎉 Web UI 全部完工，标记已写入，下轮退出驱动"
    else
      log "❌ 最终测试失败，继续修复"
      touch "$REPO/.claude/WEB_UI_FRESH_NEXT"
    fi

    # 短暂等待后检查
    sleep 60
    continue
  fi

  # 额度检查
  if ! zai_alive; then
    # 注意：此处位于主循环而非函数内，不能用 local（会报错）
    reset_time=$(date -d "5 hours" +"%F %T" 2>/dev/null || echo "5 小时后")
    log "💤 zai 额度耗尽/不可用（约5小时重置，预计 $reset_time），睡 900s 等待"
    sleep 900
    continue
  fi

  # CPU 和输出静默检测（监控逻辑已移到 pi 启动之后，见下）

  # 执行 pi 命令（Web UI 任务）
  log "▶ pi 启动 (zai-coding-cn/glm-4.7)"

  # 构建提示词
  cat > /tmp/pi-web-ui-prompt.txt <<'EOF'
你是 AI-FanYi Web UI 的自主开发工程师。

## 当前任务
继续完成 Web UI 的 tickets。请查看 `.scratch/web-ui-tickets/README.md` 了解所有 tickets 的状态和依赖关系。

## 优先级
按照依赖顺序执行未完成的 tickets。如果一个 ticket 的依赖未完成，先完成依赖项。

## 完成标准
1. 实现 ticket 中的所有功能
2. 编写测试并通过（后端 pytest，前端 vitest）
3. 更新 ticket 的 summary 文档
4. 提交代码（格式：`feat(web): 完成 Ticket XX - 标题`）
5. 推送到 GitHub

## 测试命令
- 后端测试：`cd ~/桌面/AI-FanYi && .venv/bin/python -m pytest src/filmdub/apps/web/backend/tests/ -q`
- 前端测试：`cd ~/桌面/AI-FanYi/src/filmdub/apps/web/frontend && npx vitest run`

## 重要
- 不要停下来提问，自主决策并执行
- 每完成一个 ticket 后提交并推送代码
- 遇到问题尝试修复，连续失败 3 次才标记为 blocked
- 所有 tickets 完成后输出 ALL_DONE

开始工作吧！
EOF

  # 启动 pi（后台运行，支持零输出熔断监控）
  pi --provider zai-coding-cn --model glm-4.7 < /tmp/pi-web-ui-prompt.txt >> "$LOG" 2>&1 &
  pi_pid=$!

  # 零输出熔断：后台监控 pi 进程（输出+CPU 双静默 900s 则杀掉并重试）
  (
    last_output=$(wc -l < "$LOG")
    last_cpu=$(cat /proc/$pi_pid/stat 2>/dev/null | awk '{print $14+$15}' || echo "0")
    sleep 900
    new_output=$(wc -l < "$LOG")
    new_cpu=$(cat /proc/$pi_pid/stat 2>/dev/null | awk '{print $14+$15}' || echo "0")
    if [ "$new_output" = "$last_output" ] && [ "$new_cpu" = "$last_cpu" ]; then
      log "⏳ 零输出熔断（900s 输出与 CPU 双静默）"
      pkill -TERM -P "$pi_pid" 2>/dev/null
      kill "$pi_pid" 2>/dev/null
    fi
  ) &
  monitor_pid=$!

  # 等待 pi 进程结束（不再 wait 监控子 shell，避免每轮被 900s 静默检测拖住）
  wait "$pi_pid" 2>/dev/null
  kill "$monitor_pid" 2>/dev/null

  # 检查是否需要切换会话
  if [ $((ROUND % 8)) -eq 0 ] && [ $ROUND -gt 0 ]; then
    log "🔄 每8轮预防性换新会话"
    pi session new --force >/dev/null 2>&1 || true
  fi

  # 检查 git 状态
  if [ -n "$(git status --porcelain)" ]; then
    log "✅ 检测到未提交更改，自动提交"
    git add -A
    git commit -m "chore(web-ui): 自动提交进度 (Round $ROUND)" || true
    git push origin main || log "⚠️ 推送失败，将在下次重试"
  fi

  log "一轮正常结束，30s 后继续下一轮"
  sleep 30
done

log "驱动退出"
