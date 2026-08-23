#!/bin/bash
# completion-check.sh — AI-FanYi 无人值守系统「项目完工」判定
# 判定标准（两套工单体系全部完成才算完工）：
#   1) docs/tickets/ 下所有 ticket-*.md 的状态行均为 done（正式主线工单）
#   2) .scratch/web-ui-tickets/ 下所有 NN-*.md 工单均有对应总结文件
#      （完成标志 = 存在总结文件，与 web-ui-driver.sh 的进度跟踪约定一致；
#        兼容 ticket-NN-summary.md 与 NN-xxx-summary.md 两种命名）
#
# 用法：
#   completion-check.sh               退出码 0 = 已完工；1 = 未完工（或无法判定）
#   completion-check.sh --count-webui 输出 "完成数 总数"（供进度汇报复用，避免逻辑漂移）
#
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
# 输出 "完成数 总数"；目录不存在时输出 "0 0"（视为该项无需完成）。
# glob 与 web-ui-driver.sh 的 update_tickets_progress 保持一致（[0-9]*-*.md）。
webui_count() {
    local dir="$PROJECT_DIR/.scratch/web-ui-tickets" f num total=0 done_count=0
    if [ -d "$dir" ]; then
        for f in "$dir"/[0-9]*-*.md; do
            [ -f "$f" ] || continue
            case "$f" in *-summary.md) continue ;; esac   # 排除总结文件自身
            total=$((total + 1))
            num="$(basename "$f" | cut -d'-' -f1)"
            # OR 语义：任一命名的总结文件存在即算完成。
            # 注意：ls 传多个操作数时任一缺失即整体返回非零，不能用于"任一存在"判断。
            if [ -e "$dir/ticket-$num-summary.md" ] || ls "$dir/$num-"*"-summary.md" >/dev/null 2>&1; then
                done_count=$((done_count + 1))
            fi
        done
    fi
    echo "$done_count $total"
}

webui_tickets_done() {
    local done_count total
    read -r done_count total <<< "$(webui_count)"
    [ "$total" -eq 0 ] || [ "$done_count" -eq "$total" ]
}

# ---- 入口 ----
if [ "${1:-}" = "--count-webui" ]; then
    webui_count
    exit 0
fi

if main_tickets_done && webui_tickets_done; then
    exit 0
fi
exit 1
