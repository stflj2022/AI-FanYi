"""系统状态 API"""
import psutil
import platform
from datetime import datetime
from typing import List
from sqlalchemy import select, func
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.apps.web.backend.models import User
from filmdub.apps.web.backend.api.dependencies import get_current_active_user
from filmdub.apps.web.backend.api.schemas.system_schemas import (
    SystemStatus,
    WorkerStatus,
    QueueStatus,
    SystemResourceStatus,
)
from filmdub.core.orchestrator_db import get_db
from filmdub.core.models import Job, JobStatus

router = APIRouter()


def get_system_resources() -> SystemResourceStatus:
    """获取系统资源状态"""
    # CPU
    cpu_usage = psutil.cpu_percent(interval=0.1)
    cpu_cores = psutil.cpu_count(logical=True)

    # 内存
    memory = psutil.virtual_memory()
    memory_total = memory.total // (1024 * 1024)  # MB
    memory_used = memory.used // (1024 * 1024)  # MB
    memory_usage = memory.percent

    # 磁盘
    disk = psutil.disk_usage('/')
    disk_total = disk.total // (1024 * 1024 * 1024)  # GB
    disk_used = disk.used // (1024 * 1024 * 1024)  # GB
    disk_usage = disk.percent

    # GPU（如果有）
    gpu_usage = None
    gpu_memory_usage = None
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]
            gpu_usage = gpu.load * 100
            gpu_memory_usage = (gpu.memoryUsed / gpu.memoryTotal) * 100
    except ImportError:
        pass
    except Exception:
        pass

    return SystemResourceStatus(
        cpu_usage=cpu_usage,
        cpu_cores=cpu_cores,
        memory_usage=memory_usage,
        memory_total=memory_total,
        memory_used=memory_used,
        disk_usage=disk_usage,
        disk_total=disk_total,
        disk_used=disk_used,
        gpu_usage=gpu_usage,
        gpu_memory_usage=gpu_memory_usage,
    )


def get_worker_status() -> List[WorkerStatus]:
    """获取 Worker 状态（模拟）"""
    # TODO: 从实际 Worker 管理系统获取数据
    # 返回模拟数据
    return [
        WorkerStatus(
            id="worker-1",
            name="Media Intake Worker",
            status="idle",
            type="M01",
            jobs_completed=42,
            jobs_failed=1,
            last_heartbeat=datetime.now(),
        ),
        WorkerStatus(
            id="worker-2",
            name="Research Worker",
            status="running",
            type="M02",
            jobs_completed=38,
            jobs_failed=2,
            current_job="job-123",
            last_heartbeat=datetime.now(),
        ),
    ]


def get_module_status() -> dict:
    """获取 Layer 0 模块状态（模拟）"""
    # TODO: 从实际模块状态系统获取数据
    return {
        "M01": {"status": "ready", "name": "Project & Media Intake"},
        "M02": {"status": "ready", "name": "Media Analysis"},
        "M03": {"status": "ready", "name": "Subtitle & Dialogue Acquisition"},
        "M04": {"status": "ready", "name": "Character Database Construction"},
        "M05": {"status": "ready", "name": "Audio & Scene Analysis"},
        "M06": {"status": "ready", "name": "Speaker → Character → Voice Identity"},
        "M07": {"status": "ready", "name": "Subtitle / Dialogue Intelligence"},
        "M08": {"status": "ready", "name": "Prosody & Performance Planning"},
        "M09": {"status": "ready", "name": "Voice Synthesis"},
        "M10": {"status": "ready", "name": "Dialogue Audio Processing & Scene Mixing"},
        "M11": {"status": "ready", "name": "Video Assembly & Final Encoding"},
        "M12": {"status": "ready", "name": "Project QA & Human Review"},
        "M13": {"status": "ready", "name": "Batch / Season Pipeline"},
        "M14": {"status": "ready", "name": "Project Archive & Reproducibility"},
    }


def get_system_uptime() -> float:
    """获取系统运行时间（秒）"""
    boot_time = psutil.boot_time()
    uptime = datetime.now().timestamp() - boot_time
    return uptime


async def get_queue_status(db: AsyncSession) -> QueueStatus:
    """获取队列状态"""
    try:
        # 获取各个状态的作业数量
        pending = await db.scalar(
            select(func.count(Job.id)).where(Job.status == JobStatus.PENDING)
        )
        running = await db.scalar(
            select(func.count(Job.id)).where(Job.status == JobStatus.RUNNING)
        )
        completed = await db.scalar(
            select(func.count(Job.id)).where(Job.status == JobStatus.COMPLETED)
        )
        failed = await db.scalar(
            select(func.count(Job.id)).where(Job.status == JobStatus.FAILED)
        )
        total = await db.scalar(select(func.count(Job.id)))

        return QueueStatus(
            pending=pending or 0,
            running=running or 0,
            completed=completed or 0,
            failed=failed or 0,
            total=total or 0,
        )
    except Exception:
        return QueueStatus()


@router.get("/status", response_model=SystemStatus)
async def get_system_status(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取系统状态（需要管理员权限）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )

    return SystemStatus(
        status="healthy",
        uptime=get_system_uptime(),
        resources=get_system_resources(),
        workers=get_worker_status(),
        queue=await get_queue_status(db),
        modules=get_module_status(),
    )


@router.get("/workers", response_model=List[WorkerStatus])
async def get_workers(
    current_user: User = Depends(get_current_active_user),
):
    """获取 Worker 状态（需要管理员权限）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )

    return get_worker_status()


@router.get("/queue", response_model=QueueStatus)
async def get_queue(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取队列状态（需要管理员权限）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )

    return await get_queue_status(db)
