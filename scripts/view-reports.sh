#!/bin/bash
# 查看进度汇报

REPORT_FILE="$HOME/桌面/AI-FanYi/.claude/progress-report.log"

if [ ! -f "$REPORT_FILE" ]; then
    echo "❌ 汇报日志文件不存在"
    exit 1
fi

echo "========================================"
echo "最近 3 次进度汇报"
echo "========================================"
echo ""

# 显示最近 3 次汇报
awk '/^========================================$/{count++; if(count>1 && count%2==0){print ""; print "----------------------------------------"; print ""}} {print}' "$REPORT_FILE" | tail -n +2
