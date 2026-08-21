#!/bin/bash
# 保存当前任务进度

PROGRESS_DIR=".claude"
PROGRESS_FILE="$PROGRESS_DIR/task-progress.yaml"
CONTEXT_FILE="$PROGRESS_DIR/context-summary.md"

# 创建目录
mkdir -p "$PROGRESS_DIR"

# 获取参数
TASK_ID="${1:-$(date +%Y%m%d-%H%M%S)}"
STATUS="${2:-in_progress}"
PHASE="${3:-current}"
MESSAGE="${4:-继续执行}"

# 当前时间
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# 写入进度文件
cat > "$PROGRESS_FILE" <<EOF
# 任务进度文件
# 自动生成 - 请勿手动编辑

task_id: "$TASK_ID"
started_at: "$NOW"
last_update: "$NOW"
status: "$STATUS"

current_phase:
  id: "$PHASE"
  status: "$STATUS"
  message: "$MESSAGE"
  updated_at: "$NOW"

# Claude 恢复时读取以下信息
resume_prompt: |
  从进度恢复任务: $TASK_ID
  当前阶段: $PHASE
  状态: $STATUS
  说明: $MESSAGE

  请阅读 $CONTEXT_FILE 了解详细上下文，
  然后继续执行下一个未完成的步骤。
EOF

echo "✓ 进度已保存: $PROGRESS_FILE"
echo "  任务ID: $TASK_ID"
echo "  状态: $STATUS"
echo "  阶段: $PHASE"
