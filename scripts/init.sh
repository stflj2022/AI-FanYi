#!/bin/bash
# 影视AI配音平台 - 项目初始化脚本

set -e

echo "🎬 影视AI配音平台 - 项目初始化"
echo "================================"

# 检查 Python 版本
echo "📋 检查 Python 版本..."
python3 --version || (echo "❌ Python 3.11+ 未安装" && exit 1)

# 创建虚拟环境
echo "🔧 创建虚拟环境..."
python3 -m venv venv

# 激活虚拟环境
echo "🔌 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📦 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 创建必要目录
echo "📁 创建项目目录..."
mkdir -p artifacts/{input,output,intermediate}
mkdir -p uploads/{videos,subtitles}
mkdir -p logs
mkdir -p models/{tts,asr,speaker}
mkdir -p data/{characters,voices,translations}
mkdir -p temp

# 创建 .env 文件
echo "🔐 创建环境配置..."
cat > .env << EOF
# 数据库
DATABASE_URL=postgresql://filmdubbing:filmdubbing_password@localhost:5432/filmdubbing

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=filmdubbing-artifacts

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Worker
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# 日志
LOG_LEVEL=INFO
LOG_DIR=./logs

# 路径
ARTIFACT_DIR=./artifacts
UPLOAD_DIR=./uploads
MODEL_DIR=./models
TEMP_DIR=./temp

# TMDB API (可选)
TMDB_API_KEY=

# GPU (可选)
CUDA_VISIBLE_DEVICES=0
EOF

echo "✅ 初始化完成！"
echo ""
echo "📝 下一步："
echo "1. 启动 Docker 服务: docker-compose up -d"
echo "2. 运行数据库迁移: alembic upgrade head"
echo "3. 启动 API: uvicorn src.main:app --reload"
echo "4. 启动 Worker: celery -A src.worker worker --loglevel=info"
echo ""
echo "🚀 或使用 docker-compose 一键启动所有服务"
