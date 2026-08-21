#!/bin/bash
# 保存上下文摘要

CONTEXT_FILE=".claude/context-summary.md"

echo "# 任务上下文摘要" > "$CONTEXT_FILE"
echo "" >> "$CONTEXT_FILE"
echo "**更新时间**: $(date '+%Y-%m-%d %H:%M:%S')" >> "$CONTEXT_FILE"
echo "" >> "$CONTEXT_FILE"

# 如果有输入参数，作为摘要内容
if [ -n "$1" ]; then
    echo "$1" >> "$CONTEXT_FILE"
else
    cat << 'EOF' >> "$CONTEXT_FILE"
## 当前任务

### 已完成
- 待填写...

### 进行中
- 待填写...

### 待完成
- 待填写...

### 关键决策
- 待填写...

### 技术细节
- 待填写...

### 下一步
- 待填写...
EOF
fi

echo "✓ 上下文摘要已保存: $CONTEXT_FILE"
echo ""
echo "编辑摘要:"
echo "  nano $CONTEXT_FILE"
echo ""
echo "查看摘要:"
echo "  cat $CONTEXT_FILE"
