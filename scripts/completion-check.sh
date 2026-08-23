#!/bin/bash
# completion-check.sh — AI-FanYi 无人值守系统「项目完工」判定
# 判定标准（两套工单体系全部完成才算完工）：
#   1) docs/tickets/ 下所有 ticket-*.md 的状态行均为 done（正式主线工单）
#   2) .scratch/web-ui-tickets/ 下所有 NN-*.md 工单均有对应总结文件
#      （ticket-NN-summary.md，与 web-ui-driver.sh 的进度跟踪约定一致）
# 用法：退出码 0 = 已完工；1 = 未完工（或无法判定）
# 该脚本是驱动/看门狗/进度汇报三方共享的唯一完工判据，避免各自为政。

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---- 1) 主线工单（docs/tickets）----
main_tickets_done() {
    local dir="$PROJECT_DIR/docs/tickets" f total=0 done_count=0
    [ -d "$dir" ] || return 1
    for f in "$dir"/ticket-*.md; do
        [ -f "$f" ] || continue
        total=$((total + 1))
        # 状态行形如：「## 状态: done」或「## 状态: done（第3轮复验通过：...）」
        if grep -q '^## 状态:.*done' "$f"; then
            done_count=$((done_count + 1))
        fi
    done
    [ "$total" -gt 0 ] && [ "$done_count" -eq "$total" ]
}

# ---- 2) Web UI 工单（.scratch/web-ui-tickets）----
# 完成标志 = 存在总结文件（驱动约定：完成一张工单产出 ticket-NN-summary.md）。
# 目录不存在视为该项无需完成（返回真）。
webui_tickets_done() {
    local dir="$PROJECT_DIR/.scratch/web-ui-tickets" f num total=0 done_count=0
    [ -d "$dir" ] || return 0
    for f in "$dir"/[0-9][0-9]-*.md; do
        [ -f "$f" ] || continue
        case "$f" in *-summary.md) continue ;; esac   # 排除总结文件自身
        case "$(basename "$f")" in README.md) continue ;; esac
        total=$((total + 1))
        num="$(basename "$f" | cut -d'-' -f1)"
        # 兼容两种命名：ticket-02-summary.md / 02-user-authentication-summary.md
        if ls "$dir/ticket-$num-summary.md" "$dir/$num-"*"-summary.md" >/dev/null 2>&1; then
            done_count=$((done_count + 1))
        fi
    done
    [ "$total" -eq 0 ] || [ "$done_count" -eq "$total" ]
}

if main_tickets_done && webui_tickets_done; then
    exit 0
fi
exit 1
