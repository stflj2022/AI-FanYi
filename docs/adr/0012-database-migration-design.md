# ADR 0012: 数据库迁移脚本设计

## 状态

设计中

## 上下文

使用 Alembic 进行数据库迁移管理，确保数据库 Schema 版本控制和可回滚。

## 迁移架构

```
alembic/
├── alembic.ini              # Alembic 配置
├── env.py                   # 运行时环境
├── README
├── script.py.mako           # 迁移脚本模板
└── versions/
    ├── __init__.py
    ├── 001_initial_schema.py
    ├── 002_add_voice_profiles.py
    ├── 003_add_artifact_versioning.py
    └── ...
```

## 配置文件

### alembic.ini

```ini
[alembic]
script_location = alembic
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s
timezone = Asia/Shanghai

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### env.py

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 导入配置和模型
from src.db.config import get_database_url
from src.db.models import Base

# Alembic Config 对象
config = context.config

# 解释配置文件中的 Python 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置模型的 MetaData
target_metadata = Base.metadata

def get_database_url():
    """获取数据库 URL"""
    return os.getenv('DATABASE_URL', 'postgresql://filmdubbing:filmdubbing_password@localhost:5432/filmdubbing')

def run_migrations_offline() -> None:
    """离线模式运行迁移（生成 SQL）"""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式运行迁移"""
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

## 初始迁移

### 001_initial_schema.py

```python
"""初始化数据库 Schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建初始表结构"""

    # 创建 project_status 枚举类型
    project_status_enum = postgresql.ENUM(
        'pending', 'intake', 'processing', 'review',
        'completed', 'failed', 'archived',
        name='projectstatus'
    )
    project_status_enum.create(op.get_bind())

    # 创建 job_status 枚举类型
    job_status_enum = postgresql.ENUM(
        'pending', 'scheduled', 'running', 'waiting',
        'completed', 'failed', 'cancelled', 'retrying',
        name='jobstatus'
    )
    job_status_enum.create(op.get_bind())

    # 创建 workflow_type 枚举类型
    workflow_type_enum = postgresql.ENUM(
        'single_episode', 'batch_season', 'batch_series', 'custom',
        name='workflowtype'
    )
    workflow_type_enum.create(op.get_bind())

    # 创建 artifact_type 枚举类型
    artifact_type_enum = postgresql.ENUM(
        'video', 'audio', 'subtitle', 'metadata',
        'character_db', 'voice_db', 'dialogue_timeline',
        'scene_timeline', 'analysis_result',
        'synthesis_config', 'final_video', 'qa_report',
        'archive', 'log', 'other',
        name='artifacttype'
    )
    artifact_type_enum.create(op.get_bind())

    # 创建 artifact_status 枚举类型
    artifact_status_enum = postgresql.ENUM(
        'pending', 'uploading', 'processing', 'ready',
        'failed', 'archived',
        name='artifactstatus'
    )
    artifact_status_enum.create(op.get_bind())

    # 创建 worker_status 枚举类型
    worker_status_enum = postgresql.ENUM(
        'offline', 'idle', 'busy', 'starting', 'stopping', 'error',
        name='workerstatus'
    )
    worker_status_enum.create(op.get_bind())

    # 创建 worker_type 枚举类型
    worker_type_enum = postgresql.ENUM(
        'cpu', 'gpu', 'io', 'hybrid',
        name='workertype'
    )
    worker_type_enum.create(op.get_bind())

    # 创建 projects 表
    op.create_table(
        'projects',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.VARCHAR(255), nullable=False),
        sa.Column('description', sa.TEXT(), nullable=True),
        sa.Column('status', project_status_enum, nullable=True, server_default='pending'),

        # 元数据
        sa.Column('media_type', sa.VARCHAR(50), nullable=True),
        sa.Column('title', sa.VARCHAR(255), nullable=True),
        sa.Column('title_en', sa.VARCHAR(255), nullable=True),
        sa.Column('season', sa.INTEGER(), nullable=True),
        sa.Column('episode', sa.INTEGER(), nullable=True),
        sa.Column('year', sa.INTEGER(), nullable=True),
        sa.Column('original_language', sa.VARCHAR(10), nullable=True),
        sa.Column('target_language', sa.VARCHAR(10), nullable=True, server_default='zh-CN'),

        # 外部数据源
        sa.Column('tmdb_id', sa.INTEGER(), nullable=True),
        sa.Column('imdb_id', sa.VARCHAR(20), nullable=True),

        # 时间
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),

        # 用户
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('assigned_to', sa.UUID(), nullable=True),

        # 配置
        sa.Column('workflow_id', sa.UUID(), nullable=True),
        sa.Column('config', postgresql.JSONB(), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index('ix_project_status', 'projects', ['status'])
    op.create_index('ix_project_tmdb', 'projects', ['tmdb_id'])
    op.create_index('ix_project_created', 'projects', ['created_at'])

    # 创建 jobs 表
    op.create_table(
        'jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.VARCHAR(255), nullable=False),
        sa.Column('status', job_status_enum, nullable=True, server_default='pending'),

        # 执行信息
        sa.Column('module_id', sa.VARCHAR(20), nullable=True),
        sa.Column('worker_id', sa.UUID(), nullable=True),
        sa.Column('retry_count', sa.INTEGER(), nullable=True, server_default='0'),
        sa.Column('max_retries', sa.INTEGER(), nullable=True, server_default='3'),

        # 依赖
        sa.Column('depends_on', postgresql.ARRAY(sa.UUID()), nullable=True),

        # 时间
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('scheduled_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),

        # 输入输出
        sa.Column('input_artifacts', postgresql.ARRAY(sa.UUID()), nullable=True),
        sa.Column('output_artifacts', postgresql.ARRAY(sa.UUID()), nullable=True),

        # 错误信息
        sa.Column('error_message', sa.TEXT(), nullable=True),
        sa.Column('error_stack', sa.TEXT(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE')
    )

    # 创建索引
    op.create_index('ix_job_project', 'jobs', ['project_id'])
    op.create_index('ix_job_status', 'jobs', ['status'])
    op.create_index('ix_job_module', 'jobs', ['module_id'])
    op.create_index('ix_job_worker', 'jobs', ['worker_id'])

    # 创建 workflows 表
    op.create_table(
        'workflows',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.VARCHAR(255), nullable=False),
        sa.Column('description', sa.TEXT(), nullable=True),
        sa.Column('type', workflow_type_enum, nullable=True, server_default='single_episode'),

        # 工作流定义
        sa.Column('definition', postgresql.JSONB(), nullable=False),

        # 版本控制
        sa.Column('version', sa.INTEGER(), nullable=True, server_default='1'),
        sa.Column('is_active', sa.BOOLEAN(), nullable=True, server_default='true'),

        # 时间
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index('ix_workflow_type', 'workflows', ['type'])
    op.create_index('ix_workflow_active', 'workflows', ['is_active'])

    # 创建 artifacts 表
    op.create_table(
        'artifacts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.VARCHAR(255), nullable=False),
        sa.Column('type', artifact_type_enum, nullable=False),
        sa.Column('status', artifact_status_enum, nullable=True, server_default='pending'),

        # 归属
        sa.Column('project_id', sa.UUID(), nullable=True),
        sa.Column('job_id', sa.UUID(), nullable=True),
        sa.Column('module_id', sa.VARCHAR(20), nullable=True),

        # 存储
        sa.Column('storage_type', sa.VARCHAR(20), nullable=True, server_default='minio'),
        sa.Column('storage_path', sa.TEXT(), nullable=True),
        sa.Column('storage_bucket', sa.VARCHAR(100), nullable=True),

        # 元数据
        sa.Column('size_bytes', sa.BIGINT(), nullable=True),
        sa.Column('mime_type', sa.VARCHAR(100), nullable=True),
        sa.Column('checksum', sa.VARCHAR(64), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),

        # 版本
        sa.Column('version', sa.INTEGER(), nullable=True, server_default='1'),
        sa.Column('parent_artifact_id', sa.UUID(), nullable=True),

        # 引用计数
        sa.Column('ref_count', sa.INTEGER(), nullable=True, server_default='0'),

        # 时间
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('accessed_at', sa.TIMESTAMP(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id']),
        sa.ForeignKeyConstraint(['parent_artifact_id'], ['artifacts.id'])
    )

    # 创建索引
    op.create_index('ix_artifact_project', 'artifacts', ['project_id'])
    op.create_index('ix_artifact_job', 'artifacts', ['job_id'])
    op.create_index('ix_artifact_type', 'artifacts', ['type'])
    op.create_index('ix_artifact_status', 'artifacts', ['status'])

    # 创建 workers 表
    op.create_table(
        'workers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.VARCHAR(255), nullable=False),
        sa.Column('status', worker_status_enum, nullable=True, server_default='offline'),
        sa.Column('type', worker_type_enum, nullable=True, server_default='cpu'),

        # 能力
        sa.Column('capabilities', postgresql.JSONB(), nullable=True),

        # 资源
        sa.Column('cpu_cores', sa.INTEGER(), nullable=True),
        sa.Column('memory_gb', sa.INTEGER(), nullable=True),
        sa.Column('gpu_count', sa.INTEGER(), nullable=True, server_default='0'),
        sa.Column('gpu_memory_gb', sa.INTEGER(), nullable=True, server_default='0'),

        # 当前任务
        sa.Column('current_job_id', sa.UUID(), nullable=True),

        # 统计
        sa.Column('jobs_completed', sa.INTEGER(), nullable=True, server_default='0'),
        sa.Column('jobs_failed', sa.INTEGER(), nullable=True, server_default='0'),
        sa.Column('total_runtime_seconds', sa.BIGINT(), nullable=True, server_default='0'),

        # 心跳
        sa.Column('last_heartbeat', sa.TIMESTAMP(), nullable=True),
        sa.Column('heartbeat_interval_seconds', sa.INTEGER(), nullable=True, server_default='10'),

        # 位置
        sa.Column('host', sa.VARCHAR(100), nullable=True),
        sa.Column('port', sa.INTEGER(), nullable=True),

        # 时间
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['current_job_id'], ['jobs.id'])
    )

    # 创建索引
    op.create_index('ix_worker_status', 'workers', ['status'])
    op.create_index('ix_worker_type', 'workers', ['type'])
    op.create_index('ix_worker_heartbeat', 'workers', ['last_heartbeat'])


def downgrade() -> None:
    """回滚迁移"""

    # 删除表（按依赖关系逆序）
    op.drop_table('workers')
    op.drop_table('artifacts')
    op.drop_table('workflows')
    op.drop_table('jobs')
    op.drop_table('projects')

    # 删除枚举类型
    postgresql.ENUM(name='workerstatus').drop(op.get_bind())
    postgresql.ENUM(name='workertype').drop(op.get_bind())
    postgresql.ENUM(name='artifactstatus').drop(op.get_bind())
    postgresql.ENUM(name='artifacttype').drop(op.get_bind())
    postgresql.ENUM(name='workflowtype').drop(op.get_bind())
    postgresql.ENUM(name='jobstatus').drop(op.get_bind())
    postgresql.ENUM(name='projectstatus').drop(op.get_bind())
```

## 后续迁移示例

### 002_add_voice_profiles.py

```python
"""添加人物和音色档案表

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = '001'


def upgrade() -> None:
    """创建人物和音色档案表"""

    # 创建 gender 枚举
    gender_enum = postgresql.ENUM(
        'male', 'female', 'non_binary', 'unknown',
        name='gender'
    )
    gender_enum.create(op.get_bind())

    # 创建 age_range 枚举
    age_range_enum = postgresql.ENUM(
        'child', 'teen', 'young_adult', 'adult', 'senior', 'unknown',
        name='agerange'
    )
    age_range_enum.create(op.get_bind())

    # 创建 role_type 枚举
    role_type_enum = postgresql.ENUM(
        'main', 'supporting', 'minor', 'cameo', 'background', 'unknown',
        name='roletype'
    )
    role_type_enum.create(op.get_bind())

    # 创建 characters 表
    op.create_table(
        'characters',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),

        # 基本信息
        sa.Column('name', sa.VARCHAR(255), nullable=False),
        sa.Column('name_en', sa.VARCHAR(255), nullable=True),
        sa.Column('aliases', postgresql.ARRAY(sa.VARCHAR()), nullable=True),

        # 人口统计学
        sa.Column('gender', gender_enum, nullable=True),
        sa.Column('age_range', age_range_enum, nullable=True),
        sa.Column('role_type', role_type_enum, nullable=True),

        # 演员信息
        sa.Column('actor_name', sa.VARCHAR(255), nullable=True),
        sa.Column('actor_id', sa.UUID(), nullable=True),

        # 描述
        sa.Column('description', sa.TEXT(), nullable=True),
        sa.Column('personality', sa.TEXT(), nullable=True),
        sa.Column('speech_pattern', sa.TEXT(), nullable=True),

        # 关系
        sa.Column('relationships', postgresql.JSONB(), nullable=True),

        # 首次出现
        sa.Column('first_appearance_season', sa.INTEGER(), nullable=True),
        sa.Column('first_appearance_episode', sa.INTEGER(), nullable=True),
        sa.Column('first_appearance_timestamp', sa.DECIMAL(), nullable=True),

        # 状态
        sa.Column('is_active', sa.BOOLEAN(), nullable=True, server_default='true'),
        sa.Column('voice_profile_id', sa.UUID(), nullable=True),

        # 时间
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.UniqueConstraint('project_id', 'name', name='uq_character_project_name')
    )

    # 创建索引
    op.create_index('ix_character_project', 'characters', ['project_id'])
    op.create_index('ix_character_actor', 'characters', ['actor_id'])

    # 创建 voice_profiles 表
    op.create_table(
        'voice_profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('character_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),

        # 基本信息
        sa.Column('name', sa.VARCHAR(255), nullable=False),
        sa.Column('version', sa.VARCHAR(20), nullable=True),

        # TTS 配置
        sa.Column('tts_model', sa.VARCHAR(100), nullable=True),
        sa.Column('tts_model_version', sa.VARCHAR(50), nullable=True),
        sa.Column('tts_config', postgresql.JSONB(), nullable=True),

        # 声音特征
        sa.Column('pitch_range', sa.VARCHAR(20), nullable=True),
        sa.Column('speed_range', sa.VARCHAR(20), nullable=True),
        sa.Column('emotional_range', postgresql.ARRAY(sa.VARCHAR()), nullable=True),

        # 参考音频
        sa.Column('reference_audio_artifact_id', sa.UUID(), nullable=True),

        # 状态
        sa.Column('is_active', sa.BOOLEAN(), nullable=True, server_default='true'),
        sa.Column('is_validated', sa.BOOLEAN(), nullable=True, server_default='false'),

        # 时间
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['reference_audio_artifact_id'], ['artifacts.id']),
        sa.UniqueConstraint('project_id', 'character_id', 'version', name='uq_voice_profile_version')
    )

    # 创建索引
    op.create_index('ix_voice_profile_character', 'voice_profiles', ['character_id'])
    op.create_index('ix_voice_profile_project', 'voice_profiles', ['project_id'])


def downgrade() -> None:
    """回滚迁移"""
    op.drop_table('voice_profiles')
    op.drop_table('characters')

    postgresql.ENUM(name='roletype').drop(op.get_bind())
    postgresql.ENUM(name='agerange').drop(op.get_bind())
    postgresql.ENUM(name='gender').drop(op.get_bind())
```

## 迁移管理

### 迁移命令

```bash
# 创建新迁移
alembic revision --autogenerate -m "描述信息"

# 手动创建迁移
alembic revision -m "描述信息"

# 升级到最新版本
alembic upgrade head

# 升级到特定版本
alembic upgrade +1
alembic upgrade 002

# 降级
alembic downgrade -1
alembic downgrade base

# 查看当前版本
alembic current

# 查看迁移历史
alembic history

# 生成 SQL（离线模式）
alembic upgrade head --sql > migration.sql
```

## 数据初始化

### 初始数据脚本

```python
"""初始化数据

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
import uuid


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = '002'


def upgrade() -> None:
    """插入初始数据"""

    # 创建默认工作流
    default_workflow_id = uuid.uuid4()

    op.execute(
        """
        INSERT INTO workflows (id, name, description, type, definition, version, is_active)
        VALUES (
            '{}',
            '标准单集工作流',
            '单集电视剧的标准配音处理流程',
            'single_episode',
            '{
                "nodes": [
                    {"id": "m01", "module": "M01", "config": {}},
                    {"id": "m02", "module": "M02", "config": {}},
                    {"id": "m03", "module": "M03", "config": {}},
                    {"id": "m04", "module": "M04", "config": {}},
                    {"id": "m05", "module": "M05", "config": {}},
                    {"id": "m06", "module": "M06", "config": {}},
                    {"id": "m07", "module": "M07", "config": {}},
                    {"id": "m08", "module": "M08", "config": {}},
                    {"id": "m09", "module": "M09", "config": {}},
                    {"id": "m10", "module": "M10", "config": {}},
                    {"id": "m11", "module": "M11", "config": {}},
                    {"id": "m12", "module": "M12", "config": {}}
                ],
                "edges": [
                    {"from": "m01", "to": "m02"},
                    {"from": "m01", "to": "m03"},
                    {"from": "m03", "to": "m04"},
                    {"from": "m02", "to": "m05"},
                    {"from": "m05", "to": "m06"},
                    {"from": "m04", "to": "m06"},
                    {"from": "m06", "to": "m07"},
                    {"from": "m07", "to": "m08"},
                    {"from": "m08", "to": "m09"},
                    {"from": "m09", "to": "m10"},
                    {"from": "m10", "to": "m11"},
                    {"from": "m11", "to": "m12"}
                ]
            }',
            1,
            true
        )
        """.format(str(default_workflow_id))
    )


def downgrade() -> None:
    """删除初始数据"""
    op.execute("DELETE FROM workflows WHERE name = '标准单集工作流'")
```

## 最佳实践

1. **小步迁移**: 每个迁移只做一件事
2. **可回滚**: 确保每个迁移都可以回滚
3. **幂等性**: 迁移脚本应该可以重复执行
4. **测试**: 在开发环境充分测试后再应用到生产
5. **备份**: 生产环境迁移前先备份
6. **事务**: 使用事务确保迁移原子性
