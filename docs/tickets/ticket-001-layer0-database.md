# Ticket 001: Layer 0 数据库模型和迁移

## 状态: todo（第3轮：先修测试套件再真实实现，驱动独立pytest验收）

## 优先级: 高

## 模块: Layer 0 Orchestrator

## 描述

实现 Layer 0 的核心数据库模型，使用 SQLAlchemy ORM 定义所有表结构，并使用 Alembic 管理数据库迁移。

## 任务清单

- [ ] 安装和配置 SQLAlchemy、Alembic、asyncpg
- [ ] 创建 `src/filmdub/core/database.py` - 数据库连接和会话管理
- [ ] 创建 `src/filmdub/core/models.py` - SQLAlchemy 模型定义
  - [ ] Project 模型
  - [ ] Job 模型
  - [ ] Workflow 模型
  - [ ] Artifact 模型
  - [ ] Worker 模型
  - [ ] Character 模型
  - [ ] VoiceProfile 模型
  - [ ] ErrorLog 模型
- [ ] 初始化 Alembic
- [ ] 创建初始迁移脚本
- [ ] 编写模型单元测试
- [ ] 编写数据库会话管理测试

## 依赖

无

## 输出

- 完整的数据库模型定义
- Alembic 迁移脚本
- 测试文件

## 验收标准

1. 所有模型正确定义，包含必要的索引
2. 迁移脚本可以成功执行
3. 单元测试通过率 > 90%
4. 数据库连接池配置正确

## 参考 ADR

- ADR 0002: Layer 0 数据库 Schema 设计
