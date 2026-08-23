#!/bin/bash
# completion-check.sh — AI-FanYi 无人值守系统「项目完工」判定
# 判定标准：docs/tickets/ 下所有 ticket-*.md 的状态行均为 done
# 用法：退出码 0 = 已完工；1 = 未完工（或无法判定）
# 该脚本是驱动/看门狗/进度汇报三方共享的唯一完工判据，避免各自为政。

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TICKETS_DIR="$PROJECT_DIR/docs/tickets"

# 无工单目录 → 无法判定为完工
[ -d "$TICKETS_DIR" ] || exit 1

total=0
done_count=0
for f in "$TICKETS_DIR"/ticket-*.md; do
    [ -f "$f" ] || continue
    total=$((total + 1))
    # 状态行形如：「## 状态: done」或「## 状态: done（第3轮复验通过：...）」
    if grep -q '^## 状态:.*done' "$f"; then
        done_count=$((done_count + 1))
    fi
done

# 至少有一张工单且全部 done 才算完工
if [ "$total" -gt 0 ] && [ "$done_count" -eq "$total" ]; then
    exit 0
fi
exit 1
