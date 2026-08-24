#!/bin/bash
# 停止最小执行引擎（Job Runner）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

if [ -f .claude/job-runner.pid ]; then
    PID="$(cat .claude/job-runner.pid)"
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "Job Runner 已停止 (pid $PID)"
    else
        echo "Job Runner 进程已不存在，清理 pid 文件"
    fi
    rm -f .claude/job-runner.pid
else
    echo "Job Runner 未在运行"
fi
