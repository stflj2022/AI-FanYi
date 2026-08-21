"""
作业日志存储

将作业生命周期事件持久化到文件，供 `GET /jobs/{job_id}/logs` 读取。

日志格式：每行一个 JSON 对象（JSON Lines），便于追加与流式读取。
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 默认日志根目录（可通过 ORCHESTRATOR_LOG_DIR 覆盖）
_LOG_ROOT = Path(__file__).resolve().parents[4] / "logs" / "jobs"


class JobLogStore:
    """文件型作业日志存储。"""

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = Path(log_dir) if log_dir else _LOG_ROOT

    def _path_for(self, job_id: str) -> Path:
        return self.log_dir / f"{job_id}.log"

    def append(
        self,
        job_id: str,
        event: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """追加一条日志事件。"""
        path = self._path_for(job_id)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event": event,
                "message": message,
            }
            if extra:
                entry.update(extra)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.warning("Failed to write job log for %s: %s", job_id, e)

    def read(self, job_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """读取日志事件列表（最新在前）。"""
        path = self._path_for(job_id)
        if not path.exists():
            return []
        entries: List[Dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            logger.warning("Failed to read job log for %s: %s", job_id, e)
            return []
        return list(reversed(entries[-limit:]))


# 全局实例
job_log_store = JobLogStore()
