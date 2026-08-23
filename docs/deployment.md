# AI-FanYi Web UI 部署文档

## 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [Docker Compose 部署](#docker-compose-部署)
- [生产环境部署](#生产环境部署)
- [环境变量配置](#环境变量配置)
- [数据库迁移](#数据库迁移)
- [备份与恢复](#备份与恢复)
- [故障排查](#故障排查)

## 系统要求

### 最低配置
- CPU: 4 核
- 内存: 8 GB
- 硬盘: 100 GB
- 操作系统: Ubuntu 22.04+ / Debian 12+

### 推荐配置
- CPU: 8 核
- 内存: 16 GB
- 硬盘: 500 GB SSD
- 操作系统: Ubuntu 22.04 LTS

### 依赖软件
- Docker 24.0+
- Docker Compose 2.20+
- Nginx 1.24+ (生产环境)
- PostgreSQL 15+ (或使用 Docker)
- Redis 7+ (或使用 Docker)

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/stflj2022/AI-FanYi.git
cd AI-FanYi
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的配置
```

### 3. 启动服务

```bash
docker-compose up -d
```

### 4. 访问应用

- Web UI: http://localhost:3000
- API 文档: http://localhost:8000/api/docs
- 健康检查: http://localhost:8000/health

## Docker Compose 部署

### 目录结构

```
AI-FanYi/
├── docker/
│   ├── backend/
│   │   └── Dockerfile
│   ├── frontend/
│   │   └── Dockerfile
│   ├── nginx/
│   │   └── nginx.conf
│   └── docker-compose.yml
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: filmdub-postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-filmdub}
      POSTGRES_USER: ${POSTGRES_USER:-filmdub}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-filmdub123}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-filmdub}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: filmdub-redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backend:
    build:
      context: .
      dockerfile: docker/backend/Dockerfile
    container_name: filmdub-backend
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-filmdub}:${POSTGRES_PASSWORD:-filmdub123}@postgres:5432/${POSTGRES_DB:-filmdub}
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      JWT_EXPIRATION_HOURS: ${JWT_EXPIRATION_HOURS:-24}
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:3000}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8000:8000"
    volumes:
      - ./data/projects:/app/data/projects
      - ./data/uploads:/app/data/uploads
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: docker/frontend/Dockerfile
    container_name: filmdub-frontend
    depends_on:
      - backend
    ports:
      - "3000:80"
    restart: unless-stopped

  nginx:
    image: nginx:1.24-alpine
    container_name: filmdub-nginx
    depends_on:
      - frontend
      - backend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/nginx/ssl:/etc/nginx/ssl:ro
    restart: unless-stopped

volumes:
  postgres_data:
```

### 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 停止服务并删除数据
docker-compose down -v
```

## 生产环境部署

### 1. SSL 证书配置

使用 Let's Encrypt 获取免费 SSL 证书：

```bash
# 安装 certbot
sudo apt-get update
sudo apt-get install certbot

# 获取证书
sudo certbot certonly --standalone -d your-domain.com

# 证书路径
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

### 2. Nginx 配置

生产环境 Nginx 配置示例：

```nginx
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # 上游服务器
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:80;
    }

    # HTTP 重定向到 HTTPS
    server {
        listen 80;
        server_name your-domain.com;

        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    # HTTPS 配置
    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL 证书
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        # SSL 配置
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # 安全头
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # 客户端上传大小限制
        client_max_body_size 10G;

        # 前端静态文件
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API 代理
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket 支持
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            # 超时配置
            proxy_connect_timeout 600s;
            proxy_send_timeout 600s;
            proxy_read_timeout 600s;
        }

        # WebSocket 代理
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}
```

### 3. 环境变量

生产环境 `.env` 文件：

```env
# 数据库
POSTGRES_DB=filmdub_prod
POSTGRES_USER=filmdub
POSTGRES_PASSWORD=<strong_password>

# 应用
SECRET_KEY=<strong_secret_key>
JWT_EXPIRATION_HOURS=24
DEBUG=False

# CORS
CORS_ORIGINS=https://your-domain.com

# 存储
UPLOAD_MAX_SIZE=10737418240
PROJECTS_DIR=/app/data/projects
UPLOADS_DIR=/app/data/uploads

# 日志
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log
```

## 环境变量配置说明

### 必需变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `SECRET_KEY` | JWT 签名密钥 | `your-secret-key-here` |
| `DATABASE_URL` | PostgreSQL 连接字符串 | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | Redis 连接字符串 | `redis://host:6379/0` |

### 可选变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DEBUG` | 调试模式 | `False` |
| `JWT_EXPIRATION_HOURS` | JWT 过期时间（小时） | `24` |
| `CORS_ORIGINS` | CORS 允许的源 | `*` |
| `UPLOAD_MAX_SIZE` | 最大上传大小（字节） | `10737418240` |

## 数据库迁移

### 初始化数据库

```bash
# 进入 backend 容器
docker-compose exec backend bash

# 运行迁移
alembic upgrade head

# 创建初始管理员用户
python -m scripts.create_admin
```

### 回滚迁移

```bash
# 回滚到上一个版本
alembic downgrade -1

# 回滚到特定版本
alembic downgrade <revision_id>
```

## 备份与恢复

### 数据库备份

```bash
# 备份数据库
docker-compose exec postgres pg_dump -U filmdub filmdub > backup_$(date +%Y%m%d).sql

# 压缩备份
gzip backup_$(date +%Y%m%d).sql
```

### 数据库恢复

```bash
# 解压备份
gunzip backup_20240101.sql.gz

# 恢复数据库
docker-compose exec -T postgres psql -U filmdub filmdub < backup_20240101.sql
```

### 文件备份

```bash
# 备份项目和上传文件
tar -czf data_backup_$(date +%Y%m%d).tar.gz data/
```

### 自动备份脚本

创建 `scripts/backup.sh`：

```bash
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
docker-compose exec -T postgres pg_dump -U filmdub filmdub | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# 备份文件
tar -czf $BACKUP_DIR/data_$DATE.tar.gz data/

# 删除 7 天前的备份
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

## 故障排查

### 服务无法启动

```bash
# 查看服务日志
docker-compose logs backend
docker-compose logs frontend

# 检查服务状态
docker-compose ps
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 状态
docker-compose exec postgres pg_isready -U filmdub

# 查看数据库日志
docker-compose logs postgres
```

### 前端无法访问后端

```bash
# 检查网络连接
docker-compose exec frontend ping backend

# 检查后端健康状态
curl http://localhost:8000/health
```

### WebSocket 连接失败

检查 Nginx 配置中的 WebSocket 代理设置，确保以下配置正确：

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

### 磁盘空间不足

```bash
# 检查磁盘使用情况
df -h

# 清理 Docker 资源
docker system prune -a

# 清理旧日志
docker-compose exec backend find /app/logs -name "*.log" -mtime +30 -delete
```
