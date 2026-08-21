# 影视AI配音平台 - Makefile
# 便捷的命令集合

.PHONY: help build up down restart logs shell test lint db-migrate db-upgrade db-downgrade clean install deps task-start task-save task-resume task-status task-quota

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
BLUE  := \033[0;34m
GREEN := \033[0;32m
RED   := \033[0;31m
NC    := \033[0m # No Color

# ============================================
# 帮助信息
# ============================================
help: ## 显示帮助信息
	@echo "$(BLUE)影视AI配音平台 - 可用命令$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BLUE)示例:$(NC)"
	@echo "  make build              # 构建所有镜像"
	@echo "  make up                 # 启动所有服务"
	@echo "  make logs api           # 查看 API 日志"
	@echo "  make test               # 运行测试"

# ============================================
# Docker 命令
# ============================================
build: ## 构建 Docker 镜像
	@echo "$(GREEN)构建 Docker 镜像...$(NC)"
	docker-compose build

build-dev: ## 构建开发环境镜像
	@echo "$(GREEN)构建开发环境镜像...$(NC)"
	BUILD_TARGET=development docker-compose build

build-api: ## 只构建 API 镜像
	@echo "$(GREEN)构建 API 镜像...$(NC)"
	docker-compose build api

build-worker: ## 只构建 Worker 镜像
	@echo "$(GREEN)构建 Worker 镜像...$(NC)"
	docker-compose build worker

up: ## 启动所有服务
	@echo "$(GREEN)启动所有服务...$(NC)"
	docker-compose up -d

up-dev: ## 启动开发环境（带热重载）
	@echo "$(GREEN)启动开发环境...$(NC)"
	BUILD_TARGET=development docker-compose up

up-api: ## 只启动 API 服务
	@echo "$(GREEN)启动 API 服务...$(NC)"
	docker-compose up -d api

up-worker: ## 只启动 Worker 服务
	@echo "$(GREEN)启动 Worker 服务...$(NC)"
	docker-compose up -d worker

down: ## 停止所有服务
	@echo "$(RED)停止所有服务...$(NC)"
	docker-compose down

restart: ## 重启所有服务
	@echo "$(GREEN)重启所有服务...$(NC)"
	docker-compose restart

logs: ## 查看所有服务日志
	docker-compose logs -f

logs-api: ## 查看 API 日志
	docker-compose logs -f api

logs-worker: ## 查看 Worker 日志
	docker-compose logs -f worker

logs-db: ## 查看数据库日志
	docker-compose logs -f postgres

shell: ## 进入 API 容器
	docker-compose exec api bash

shell-db: ## 进入数据库容器
	docker-compose exec postgres psql -U filmdubbing -d filmdubbing

shell-redis: ## 进入 Redis 容器
	docker-compose exec redis redis-cli

ps: ## 查看运行状态
	docker-compose ps

# ============================================
# 开发命令
# ============================================
install: ## 安装依赖
	@echo "$(GREEN)安装 Python 依赖...$(NC)"
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

deps: ## 更新依赖
	@echo "$(GREEN)更新依赖...$(NC)"
	pip-compile requirements.in
	pip-compile requirements-dev.in

lint: ## 代码质量检查
	@echo "$(GREEN)运行代码质量检查...$(NC)"
	ruff check src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/

format: ## 格式化代码
	@echo "$(GREEN)格式化代码...$(NC)"
	ruff check --fix src/ tests/
	black src/ tests/
	isort src/ tests/

test: ## 运行所有测试
	@echo "$(GREEN)运行测试...$(NC)"
	pytest

test-unit: ## 运行单元测试
	@echo "$(GREEN)运行单元测试...$(NC)"
	pytest tests/unit/

test-integration: ## 运行集成测试
	@echo "$(GREEN)运行集成测试...$(NC)"
	pytest tests/integration/

test-coverage: ## 运行测试并生成覆盖率报告
	@echo "$(GREEN)生成覆盖率报告...$(NC)"
	pytest --cov=src --cov-report=html --cov-report=term

# ============================================
# 数据库命令
# ============================================
db-migrate: ## 创建新的迁移
	@echo "$(GREEN)创建数据库迁移...$(NC)"
	alembic revision --autogenerate -m "$(MESSAGE)"

db-upgrade: ## 执行数据库迁移
	@echo "$(GREEN)执行数据库迁移...$(NC)"
	docker-compose exec api alembic upgrade head

db-downgrade: ## 回滚上一个迁移
	@echo "$(RED)回滚数据库迁移...$(NC)"
	docker-compose exec api alembic downgrade -1

db-reset: ## 重置数据库
	@echo "$(RED)重置数据库...$(NC)"
	docker-compose down -v
	docker-compose up -d postgres
	sleep 5
	docker-compose up -d api
	docker-compose exec api alembic upgrade head

# ============================================
# 清理命令
# ============================================
clean: ## 清理临时文件
	@echo "$(RED)清理临时文件...$(NC)"
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ .pytest_cache/

clean-docker: ## 清理 Docker 资源
	@echo "$(RED)清理 Docker 资源...$(NC)"
	docker-compose down -v
	docker system prune -f

clean-all: clean clean-docker ## 清理所有（包括 Docker）

# ============================================
# 生产命令
# ============================================
prod-build: ## 生产环境构建
	@echo "$(GREEN)构建生产镜像...$(NC)"
	docker-compose -f docker-compose.yml --env-file .env build

prod-up: ## 生产环境启动
	@echo "$(GREEN)启动生产环境...$(NC)"
	docker-compose -f docker-compose.yml --env-file .env up -d

prod-logs: ## 生产环境日志
	docker-compose -f docker-compose.yml --env-file .env logs -f

# ============================================
# 监控命令
# ============================================
stats: ## 查看容器资源使用
	docker stats

health: ## 检查服务健康状态
	@echo "$(GREEN)检查服务健康...$(NC)"
	@curl -sf http://localhost:8000/health && echo "✓ API: OK" || echo "✗ API: FAIL"
	@docker-compose exec postgres pg_isready -U filmdubbing && echo "✓ DB: OK" || echo "✗ DB: FAIL"
	@docker-compose exec redis redis-cli ping && echo "✓ Redis: OK" || echo "✗ Redis: FAIL"

# ============================================
# 工具命令
# ============================================
init: ## 初始化项目
	@echo "$(GREEN)初始化项目...$(NC)"
	@mkdir -p artifacts uploads logs temp models
	@cp .env.example .env
	@echo "$(GREEN)✓ 目录结构创建完成$(NC)"
	@echo "$(BLUE)请编辑 .env 文件配置环境变量$(NC)"

backup-db: ## 备份数据库
	@echo "$(GREEN)备份数据库...$(NC)"
	docker-compose exec postgres pg_dump -U filmdubbing filmdubbing > backup_$$(date +%Y%m%d_%H%M%S).sql

restore-db: ## 恢复数据库（用法: make restore-db FILE=backup.sql）
	@echo "$(GREEN)恢复数据库...$(NC)"
	docker-compose exec -T postgres psql -U filmdubbing filmdubbing < $(FILE)

# ============================================
# GPU 支持
# ============================================
gpu-up: ## 启动 GPU Worker
	@echo "$(GREEN)启动 GPU Worker...$(NC)"
	docker-compose --profile gpu up -d gpu-worker

gpu-logs: ## 查看 GPU Worker 日志
	docker-compose logs -f gpu-worker

# ============================================
# 监控支持
# ============================================
monitoring-up: ## 启动监控服务（Flower）
	@echo "$(GREEN)启动监控服务...$(NC)"
	docker-compose --profile monitoring up -d flower

	@echo "$(GREEN)✓ 监控服务已启动$(NC)"
	@echo "$(BLUE)访问 http://localhost:5555 查看 Celery 监控$(NC)"

nginx-up: ## 启动 Nginx 反向代理
	@echo "$(GREEN)启动 Nginx...$(NC)"
	docker-compose --profile nginx up -d nginx

# ============================================
# 发布命令
# ============================================
release: ## 创建发布（需要 tag）
	@if [ -z "$(VERSION)" ]; then \
		echo "$(RED)错误: 请指定版本号，例如: make release VERSION=1.0.0$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)创建发布 $(VERSION)...$(NC)"
	git tag -a v$(VERSION) -m "Release v$(VERSION)"
	git push origin v$(VERSION)

# ============================================
# 任务管理命令（长期任务进度保存）
# ============================================
task-start: ## 开始新任务 (用法: make task-start TASK_ID=implement-m01)
	@$(if $(TASK_ID),,$(error 请指定 TASK_ID，例如: make task-start TASK_ID=implement-m01))
	@echo "$(GREEN)开始任务: $(TASK_ID)$(NC)"
	@bash .claude/scripts/task-manager.sh start $(TASK_ID)

task-save: ## 保存当前进度 (用法: make task-save PHASE=api-endpoints MESSAGE="完成CRUD")
	@echo "$(GREEN)保存任务进度...$(NC)"
	@bash .claude/scripts/task-manager.sh progress $(PHASE) "$(MESSAGE)"
	@echo ""
	@echo "$(BLUE)提示: 同时保存上下文摘要$(NC)"
	@echo "  make task-context SUMMARY='已完成数据库模型，下一步API实现'"

task-context: ## 保存上下文摘要
	@echo "$(GREEN)保存上下文摘要...$(NC)"
	@bash .claude/scripts/task-manager.sh context "$(SUMMARY)"

task-resume: ## 从进度恢复任务
	@echo "$(GREEN)恢复任务...$(NC)"
	@bash .claude/scripts/task-manager.sh resume

task-status: ## 查看当前任务状态
	@echo "$(GREEN)当前任务状态:$(NC)"
	@echo ""
	@bash .claude/scripts/task-manager.sh status

task-quota: ## 检查 API 额度
	@echo "$(GREEN)检查 API 额度...$(NC)"
	@bash .claude/scripts/task-manager.sh quota

task-backup: ## 备份完整任务状态
	@echo "$(GREEN)备份任务状态...$(NC)"
	@bash .claude/scripts/task-manager.sh save

# ============================================
# 额度等待命令
# ============================================
wait-reset: ## 等待额度重置后继续
	@echo "$(GREEN)等待智谱 API 额度重置...$(NC)"
	@echo "$(BLUE)当前时间: $$(date '+%Y-%m-%d %H:%M:%S')$(NC)"
	@echo ""
	@python3 .claude/scripts/check-quota.py || true
	@echo ""
	@echo "$(BLUE)提示: 重置时间约每5小时一次$(NC)"
	@echo "$(BLUE)重置后运行: make task-resume$(NC)"

# ============================================
# 自动任务执行（无人值守）
# ============================================
auto-start: ## 启动自动任务编排器
	@echo "$(GREEN)启动自动任务编排器...$(NC)"
	@chmod +x .claude/scripts/*.sh .claude/scripts/*.py
	@python3 .claude/scripts/auto-orchestrator.py

auto-check: ## 检查额度和状态
	@echo "$(GREEN)检查自动任务状态...$(NC)"
	@python3 .claude/scripts/auto-orchestrator.py --check

auto-save: ## 自动保存检查点 (用法: make auto-save PHASE=x MSG="y" NEXT="z")
	@python3 .claude/scripts/auto-orchestrator.py --save $(PHASE) "$(MESSAGE)" "$(NEXT)" "$(CONTEXT)"

auto-resume: ## 生成恢复指令
	@echo "$(GREEN)生成恢复指令...$(NC)"
	@python3 .claude/scripts/auto-orchestrator.py --resume

auto-wait: ## 等待额度重置
	@echo "$(GREEN)等待额度重置...$(NC)"
	@python3 .claude/scripts/auto-orchestrator.py --wait

# ============================================
# 一键执行（保存+等待+恢复指令）
# ==============================================
checkpoint-and-wait: ## 保存检查点并等待重置
	@echo "$(GREEN)保存检查点并等待重置...$(NC)"
	@$(MAKE) auto-save PHASE=$(PHASE) MESSAGE="$(MESSAGE)" NEXT="$(NEXT)" CONTEXT="$(CONTEXT)"
	@echo ""
	@$(MAKE) auto-wait

full-cycle: ## 完整周期：检查→保存→等待→生成恢复指令
	@echo "$(GREEN)执行完整周期...$(NC)"
	@echo ""
	@echo "1️⃣ 检查额度..."
	@$(MAKE) auto-check
	@echo ""
	@echo "2️⃣ 保存检查点..."
	@$(MAKE) auto-save PHASE=$(PHASE) MESSAGE="$(MESSAGE)" NEXT="$(NEXT)" CONTEXT="$(CONTEXT)"
	@echo ""
	@echo "3️⃣ 等待重置..."
	@$(MAKE) auto-wait
	@echo ""
	@echo "4️⃣ 生成恢复指令..."
	@$(MAKE) auto-resume > .claude/RESUME.txt
	@echo "$(GREEN)✓ 完整周期完成$(NC)"
	@echo "$(BLUE)恢复指令已保存到 .claude/RESUME.txt$(NC)"
