#!/bin/bash
# 启动最小执行引擎（Job Runner）
# 轮询 orchestrator DB 中的 pending/scheduled 配音任务并自动执行 M01 媒体分析
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# 数据库（docker postgres 宿主映射）
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://filmdubbing:filmdubbing_password@localhost:5432/filmdubbing}"
# MinIO（docker minio 宿主映射）
export MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:9000}"
export MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
export MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin123}"

# 已运行则跳过
if [ -f .claude/job-runner.pid ] && kill -0 "$(cat .claude/job-runner.pid)" 2>/dev/null; then
    echo "Job Runner 已在运行 (pid $(cat .claude/job-runner.pid))"
    exit 0
fi

mkdir -p .claude
nohup .venv/bin/python -m filmdub.orchestrator.job_runner 5 >> .claude/job-runner.log 2>&1 &
echo $! > .claude/job-runner.pid
echo "Job Runner 已启动 (pid $(cat .claude/job-runner.pid))"
echo "日志: .claude/job-runner.log"
