"""系统状态相关的 Pydantic schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class WorkerStatus(BaseModel):
    """Worker 状态"""
    id: str
    name: str
    status: str
    type: str
    jobs_completed: int = 0
    jobs_failed: int = 0
    current_job: Optional[str] = None
    last_heartbeat: Optional[datetime] = None


class QueueStatus(BaseModel):
    """队列状态"""
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    total: int = 0


class SystemResourceStatus(BaseModel):
    """系统资源状态"""
    cpu_usage: float = 0.0  # CPU 使用率 (0-100)
    cpu_cores: int = 1
    memory_usage: float = 0.0  # 内存使用率 (0-100)
    memory_total: int = 0  # 总内存（MB）
    memory_used: int = 0  # 已用内存（MB）
    disk_usage: float = 0.0  # 磁盘使用率 (0-100)
    disk_total: int = 0  # 总磁盘空间（GB）
    disk_used: int = 0  # 已用磁盘空间（GB）
    gpu_usage: Optional[float] = None  # GPU 使用率 (0-100)，如果没有 GPU 则为 None
    gpu_memory_usage: Optional[float] = None  # GPU 内存使用率 (0-100)


class SystemStatus(BaseModel):
    """系统状态"""
    status: str = "healthy"
    uptime: float = 0.0  # 运行时间（秒）
    resources: SystemResourceStatus
    workers: List[WorkerStatus] = []
    queue: QueueStatus
    modules: dict = {}  # Layer 0 模块状态
