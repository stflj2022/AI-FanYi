#!/bin/bash
# 从进度恢复任务

PROGRESS_FILE=".claude/task-progress.yaml"
CONTEXT_FILE=".claude/context-summary.md"

echo "======================================"
echo "从进度恢复任务"
echo "======================================"
echo ""

# 检查进度文件
if [ ! -f "$PROGRESS_FILE" ]; then
    echo "❌ 未找到进度文件: $PROGRESS_FILE"
    echo ""
    echo "请确认:"
    echo "  1. 是否有正在进行的任务"
    echo "  2. 进度文件是否存在"
    echo ""
    echo "可用的进度文件:"
    ls -la .claude/*.yaml 2>/dev/null || echo "  (无)"
    exit 1
fi

echo "📋 进度信息:"
echo ""
cat "$PROGRESS_FILE"
echo ""

# 读取恢复提示
if [ -f "$CONTEXT_FILE" ]; then
    echo "📖 上下文摘要:"
    echo ""
    cat "$CONTEXT_FILE"
    echo ""
fi

echo "======================================"
echo "恢复指令"
echo "======================================"
echo ""
echo "复制以下指令给 Claude 继续任务:"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
cat "$PROGRESS_FILE" | grep -A 5 "resume_prompt:" | sed 's/resume_prompt:|//' | sed 's/^[ ]*//' | grep -v '^$' | sed 's/^/  /'
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "或者查看完整进度文件:"
echo "  cat $PROGRESS_FILE"
