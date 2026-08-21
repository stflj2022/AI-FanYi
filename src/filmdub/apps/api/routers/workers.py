"""
Worker 管理 API 路由（Ticket 004）

提供 Worker 注册、心跳、状态查询和注销端点，全部委托给 WorkerManager，
心跳/注销通过 JWT Token 认证（Worker 注册时签发）。
"""
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.orchestrator.database import get_db
from filmdub.orchestrator.jwt_handler import JWTHandler
from filmdub.orchestrator.models import WorkerType
from filmdub.orchestrator.worker_manager import WorkerManager

router = APIRouter(prefix="/workers", tags=["workers"])


# ==================== 请求模型 ====================


class WorkerRegisterRequest(BaseModel):
    """Worker 注册请求"""
    name: str = Field(..., min_length=1, max_length=255)
    worker_type: str = Field("cpu", pattern="^(cpu|gpu|io|hybrid)$")
    capabilities: Optional[Dict[str, Any]] = None
    cpu_cores: int = Field(4, ge=1, le=1024)
    memory_gb: int = Field(16, ge=1, le=4096)
    gpu_count: int = Field(0, ge=0, le=64)
    gpu_memory_gb: int = Field(0, ge=0)
    host: str = Field("localhost", max_length=100)
    port: int = Field(8001, ge=1, le=65535)


class WorkerHeartbeatRequest(BaseModel):
    """Worker 心跳请求"""
    status: str = Field("idle", pattern="^(offline|idle|busy|starting|stopping|error)$")
    current_job_id: Optional[uuid.UUID] = None
    statistics: Optional[Dict[str, Any]] = None


# ==================== 认证依赖 ====================


def _get_jwt_handler() -> JWTHandler:
    return JWTHandler()


async def require_worker_auth(
    worker_id: uuid.UUID,
    authorization: Optional[str] = Header(None),
    jwt: JWTHandler = Depends(_get_jwt_handler),
) -> None:
    """校验 Worker Token：必须是该 Worker 的、类型为 worker 且未过期。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
        )
    token = authorization.removeprefix("Bearer ").strip()
    payload = jwt.verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if payload.get("worker_id") != str(worker_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not match worker",
        )


# ==================== 端点 ====================


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_worker(
    req: WorkerRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """注册 Worker，返回 Worker 信息与 JWT Token。"""
    manager = WorkerManager(db)
    result = await manager.register_worker(
        name=req.name,
        worker_type=WorkerType(req.worker_type),
        capabilities=req.capabilities,
        cpu_cores=req.cpu_cores,
        memory_gb=req.memory_gb,
        gpu_count=req.gpu_count,
        gpu_memory_gb=req.gpu_memory_gb,
        host=req.host,
        port=req.port,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result["message"],
        )
    return result


@router.post("/{worker_id}/heartbeat")
async def worker_heartbeat(
    worker_id: uuid.UUID,
    req: WorkerHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_worker_auth),
) -> Dict[str, Any]:
    """Worker 心跳，返回待处理指令。"""
    manager = WorkerManager(db)
    result = await manager.handle_heartbeat(
        worker_id=worker_id,
        status=req.status,
        current_job_id=req.current_job_id,
        statistics=req.statistics,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"],
        )
    return result


@router.get("")
async def list_workers(
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """获取 Worker 列表。"""
    manager = WorkerManager(db)
    return await manager.list_workers()


@router.get("/{worker_id}")
async def get_worker(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """获取 Worker 详情。"""
    manager = WorkerManager(db)
    worker = await manager.get_worker(worker_id)
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )
    return worker


@router.post("/{worker_id}/unregister")
async def unregister_worker(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_worker_auth),
) -> Dict[str, Any]:
    """注销 Worker（标记为停止中）。"""
    manager = WorkerManager(db)
    ok = await manager.unregister_worker(worker_id)
    if not ok:
        worker = await manager.get_worker(worker_id)
        if worker is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Worker {worker_id} not found",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Worker {worker_id} has a running job and cannot be unregistered",
        )
    worker = await manager.get_worker(worker_id)
    return worker
