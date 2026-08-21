"""
Worker 运行时通用工具

为各模块 Worker 提供作业轮询与 Artifact 持久化的通用实现，
避免每个 Worker 重复编写相同的通信循环样板代码。
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL = 5.0


def save_json_artifact(
    project_id: str,
    artifact_type: str,
    data: Dict[str, Any],
    projects_base_dir: Optional[Path] = None,
) -> str:
    """将处理结果以 JSON 形式持久化到项目 Artifact 目录。

    Args:
        project_id: 项目 ID
        artifact_type: Artifact 类型（如 ``character_db``、``mapping``）
        data: 要保存的字典数据
        projects_base_dir: 项目基目录，默认为 ``./artifacts``

    Returns:
        写入文件的绝对路径
    """
    base = Path(projects_base_dir) if projects_base_dir else Path("./artifacts")
    artifact_dir = base / project_id / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    path = artifact_dir / f"{artifact_type}.json"
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    logger.debug(f"Artifact saved: {path}")
    return str(path)


async def run_worker_loop(
    worker_name: str,
    process_job: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]],
    queue_dir: str | Path,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    max_jobs: Optional[int] = None,
) -> int:
    """运行 Worker 作业轮询循环。

    从 ``queue_dir`` 中读取 ``*.json`` 作业文件，依次处理并写回
    ``<job>.result.json``。这是基于文件系统的真实作业通信循环，
    与 Artifact 架构一致（ADR 0001 / ADR 0006）。

    Args:
        worker_name: Worker 名称（用于日志）
        process_job: 处理单个作业的异步函数，接收作业字典，返回结果字典
        queue_dir: 作业队列目录
        poll_interval: 轮询间隔（秒）
        max_jobs: 处理的最大作业数，为 None 表示无限循环

    Returns:
        成功处理的作业数量
    """
    queue = Path(queue_dir)
    queue.mkdir(parents=True, exist_ok=True)

    logger.info(f"{worker_name} worker started, polling {queue}")

    processed = 0
    seen: set[str] = set()

    try:
        while max_jobs is None or processed < max_jobs:
            jobs = sorted(queue.glob("*.job.json"))

            for job_file in jobs:
                key = job_file.name
                result_file = job_file.with_name(job_file.name.replace(".job.json", ".result.json"))

                if key in seen and result_file.exists():
                    continue

                seen.add(key)

                try:
                    job_data = json.loads(job_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as e:
                    logger.error(f"Failed to read job file {job_file}: {e}")
                    continue

                result = await process_job(job_data)
                result_file.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8",
                )
                processed += 1

            if max_jobs is not None and processed >= max_jobs:
                break

            await asyncio.sleep(poll_interval)
    except asyncio.CancelledError:
        logger.info(f"{worker_name} worker loop cancelled")
        raise
    finally:
        logger.info(f"{worker_name} worker stopped, processed {processed} jobs")

    return processed
