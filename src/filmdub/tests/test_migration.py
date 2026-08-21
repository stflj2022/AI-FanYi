"""
Ticket 001 数据库迁移测试

验证 Alembic 迁移脚本可以在 SQLite 上完整执行，且生成的表结构与模型元数据一致。
"""
import os
import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def _run_alembic_upgrade(tmp_db: Path) -> None:
    """在临时 SQLite 数据库上执行 alembic upgrade head。"""
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{tmp_db}"
    # 让 alembic 在项目根目录运行
    import subprocess
    import sys
    venv_bin = Path(sys.executable).parent
    result = subprocess.run(
        [str(venv_bin / "alembic"), "-c", "alembic.ini", "upgrade", "head"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, f"alembic upgrade failed:\n{result.stdout}\n{result.stderr}"


EXPECTED_TABLES = {
    "alembic_version",
    "artifacts",
    "characters",
    "error_log",
    "jobs",
    "projects",
    "voice_profiles",
    "workers",
    "workflows",
}


def test_alembic_upgrade_creates_all_tables(tmp_path):
    """迁移脚本可以成功执行并创建全部表。"""
    tmp_db = tmp_path / "migration.db"
    _run_alembic_upgrade(tmp_db)

    conn = sqlite3.connect(tmp_db)
    try:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        conn.close()

    assert EXPECTED_TABLES.issubset(tables), f"缺少表: {EXPECTED_TABLES - tables}"


def test_alembic_upgrade_is_idempotent(tmp_path):
    """重复执行迁移不应报错（alembic_version 已是最新）。"""
    tmp_db = tmp_path / "migration.db"
    _run_alembic_upgrade(tmp_db)
    # 第二次执行应当无操作且成功
    _run_alembic_upgrade(tmp_db)


def test_alembic_migration_matches_models(tmp_path):
    """迁移后的数据库可以使用 orchestrator 模型执行 CRUD。"""
    tmp_db = tmp_path / "migration.db"
    _run_alembic_upgrade(tmp_db)

    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{tmp_db}"

    import importlib
    import filmdub.orchestrator.config as orch_config
    import filmdub.orchestrator.database as orch_db

    # 重新加载模块以应用新的 DATABASE_URL
    importlib.reload(orch_config)
    importlib.reload(orch_db)

    from filmdub.orchestrator.models import Project, ProjectStatus
    from sqlalchemy import select

    async def _run():
        async with orch_db.get_db_context() as db:
            project = Project(
                name="Migration Test",
                status=ProjectStatus.PENDING,
                title="Migration Test Title",
                target_language="zh-CN",
            )
            db.add(project)
            await db.flush()
            assert project.id is not None

            result = await db.execute(
                select(Project).where(Project.name == "Migration Test")
            )
            assert result.scalar_one().id == project.id

    import asyncio
    asyncio.run(_run())
    importlib.reload(orch_config)
    importlib.reload(orch_db)
