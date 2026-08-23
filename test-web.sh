#!/bin/bash
# Web UI 测试脚本

cd /home/wu/桌面/AI-FanYi/src/filmdub/apps/web/frontend

if [ "$1" == "backend" ]; then
  echo "运行后端测试..."
  cd /home/wu/桌面/AI-FanYi
  .venv/bin/python -m pytest src/filmdub/apps/web/backend/tests/ -q
elif [ "$1" == "frontend" ]; then
  echo "运行前端测试..."
  cd /home/wu/桌面/AI-FanYi/src/filmdub/apps/web/frontend
  npx vitest run
elif [ "$1" == "all" ]; then
  echo "运行所有测试..."
  echo "========================================"
  echo "后端测试:"
  echo "========================================"
  cd /home/wu/桌面/AI-FanYi
  .venv/bin/python -m pytest src/filmdub/apps/web/backend/tests/ -q
  echo ""
  echo "========================================"
  echo "前端测试:"
  echo "========================================"
  cd /home/wu/桌面/AI-FanYi/src/filmdub/apps/web/frontend
  npx vitest run
else
  echo "用法: $0 {backend|frontend|all}"
  exit 1
fi
