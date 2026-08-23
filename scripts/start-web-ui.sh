#!/bin/bash
# Web UI 启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  AI-FanYi Web UI 启动脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}错误: Docker 未运行，请先启动 Docker${NC}"
    exit 1
fi

# 检查 .env 文件
if [ ! -f .env ]; then
    echo -e "${YELLOW}未找到 .env 文件，从 .env.example 创建...${NC}"
    cp .env.example .env
    echo -e "${GREEN}已创建 .env 文件，请根据需要修改配置${NC}"
fi

# 启动基础设施（含 postgres）
echo -e "${YELLOW}启动基础设施（postgres/redis/minio）...${NC}"
docker-compose up -d postgres redis minio minio-init

# 等待 postgres 就绪（冷启动时容器未启动，必须先就绪再迁移）
echo -e "${YELLOW}等待 postgres 就绪...${NC}"
for i in $(seq 1 30); do
    if docker-compose exec -T postgres pg_isready -U ${POSTGRES_USER:-filmdubbing} >/dev/null 2>&1; then
        break
    fi
    sleep 2
done
if ! docker-compose exec -T postgres pg_isready -U ${POSTGRES_USER:-filmdubbing} >/dev/null 2>&1; then
    echo -e "${RED}错误: postgres 未在 60s 内就绪，请检查 docker-compose logs postgres${NC}"
    exit 1
fi

# 运行数据库迁移（postgres 已就绪；不再用 || true 静默吞错）
echo -e "${YELLOW}运行数据库迁移...${NC}"
if ! docker-compose exec -T postgres psql -U ${POSTGRES_USER:-filmdubbing} -d ${POSTGRES_DB:-filmdubbing} <<'EOF'
-- 检查 users 表是否存在
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'users') THEN
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            is_admin BOOLEAN DEFAULT false NOT NULL,
            is_active BOOLEAN DEFAULT true NOT NULL,
            created_at TIMESTAMP DEFAULT now() NOT NULL,
            updated_at TIMESTAMP DEFAULT now() NOT NULL
        );
        CREATE INDEX idx_users_username ON users(username);
        CREATE INDEX idx_users_email ON users(email);
        CREATE INDEX idx_users_is_active ON users(is_active);
    END IF;

    -- 检查 projects 表是否有 owner_id 列
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'projects' AND column_name = 'owner_id'
    ) THEN
        ALTER TABLE projects ADD COLUMN owner_id UUID;
        ALTER TABLE projects ADD CONSTRAINT fk_projects_owner_id
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE;
    END IF;

    -- 检查 projects 表是否有 cover_image_url 列
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'projects' AND column_name = 'cover_image_url'
    ) THEN
        ALTER TABLE projects ADD COLUMN cover_image_url VARCHAR(500);
    END IF;

    -- 检查 jobs 表是否有 user_friendly_status 列
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'jobs' AND column_name = 'user_friendly_status'
    ) THEN
        ALTER TABLE jobs ADD COLUMN user_friendly_status VARCHAR(100);
    END IF;

    -- 检查 jobs 表是否有 user_friendly_error 列
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'jobs' AND column_name = 'user_friendly_error'
    ) THEN
        ALTER TABLE jobs ADD COLUMN user_friendly_error TEXT;
    END IF;

    -- 检查 characters 表是否有 avatar_url 列
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'characters' AND column_name = 'avatar_url'
    ) THEN
        ALTER TABLE characters ADD COLUMN avatar_url VARCHAR(500);
    END IF;

    -- 检查 characters 表是否有 first_appearance_episode_name 列
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'characters' AND column_name = 'first_appearance_episode_name'
    ) THEN
        ALTER TABLE characters ADD COLUMN first_appearance_episode_name VARCHAR(255);
    END IF;
END $$;
EOF
then
    echo -e "${RED}数据库迁移失败${NC}"
    exit 1
fi

echo -e "${GREEN}数据库迁移完成${NC}"

# 启动 Web UI 服务
echo -e "${YELLOW}启动 Web UI 服务...${NC}"
docker-compose up -d web-backend web-frontend

# 等待服务启动
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 10

# 检查服务健康状态
echo -e "${YELLOW}检查服务健康状态...${NC}"

# 检查后端
if curl -f http://localhost:8001/api/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Web Backend 运行正常 (http://localhost:8001)${NC}"
else
    echo -e "${RED}✗ Web Backend 启动失败${NC}"
    docker-compose logs web-backend --tail=50
fi

# 检查前端
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Web Frontend 运行正常 (http://localhost:3000)${NC}"
else
    echo -e "${RED}✗ Web Frontend 启动失败${NC}"
    docker-compose logs web-frontend --tail=50
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Web UI 启动完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${YELLOW}前端地址: http://localhost:3000${NC}"
echo -e "${YELLOW}后端 API: http://localhost:8001/api/v1/docs${NC}"
echo -e "${YELLOW}健康检查: http://localhost:8001/api/v1/health${NC}"
echo -e "${GREEN}========================================${NC}"
