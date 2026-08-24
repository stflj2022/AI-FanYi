"""WebSocket 事件路由

提供 WebSocket 连接端点，支持任务事件订阅和实时推送
"""
import json
import uuid
from uuid import UUID
from typing import Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, status
from starlette.websockets import WebSocketState
from sqlalchemy.ext.asyncio import AsyncSession

from filmdub.core.config import settings
from filmdub.core.orchestrator_db import get_db
from filmdub.apps.web.backend.websocket.manager import ws_manager
from filmdub.apps.web.backend.websocket.event_types import (
    WebSocketEventType,
    SubscribeRequest,
    build_event,
    build_error_event,
)
from filmdub.apps.web.backend.services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_current_user_ws(
    websocket: WebSocket,
    token: str = Query(None, description="JWT 认证令牌"),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    """WebSocket JWT 认证依赖（本地免登录模式下不校验 Token）"""
    # 本地免登录模式：返回与 HTTP 一致的本地用户真实 ID（保证实时事件能匹配）
    if settings.auth_disabled:
        from filmdub.apps.web.backend.api.dependencies import _get_or_create_local_user
        user = await _get_or_create_local_user(db)
        return user.id

    try:
        # 验证 token 并获取 user_id
        user_id = await AuthService.verify_token(token)
        return UUID(user_id)
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        raise


@router.websocket("/jobs")
async def websocket_jobs_endpoint(
    websocket: WebSocket,
    token: str = Query(None, description="JWT 认证令牌"),
    connection_id: str = Query(None, description="连接 ID（可选）"),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket 任务事件端点

    支持订阅任务事件，实时接收：
    - 任务进度更新 (job.progress)
    - 任务阶段变化 (job.stage)
    - 任务完成 (job.completed)
    - 任务失败 (job.failed)

    连接格式:
        ws://host:port/api/v1/ws/jobs?token=YOUR_JWT_TOKEN

    订阅任务:
        {"action": "subscribe", "job_id": "uuid"}

    取消订阅:
        {"action": "unsubscribe", "job_id": "uuid"}

    心跳响应:
        {"type": "ping"} -> {"type": "pong"}
    """
    # 生成连接 ID
    if not connection_id:
        connection_id = str(uuid.uuid4())

    try:
        # 认证
        user_id = await get_current_user_ws(websocket, token, db)

        # 建立连接
        connection = await ws_manager.connect(websocket, user_id, connection_id)

        # 发送连接成功消息
        await connection.send(build_event(
            event_type=WebSocketEventType.CONNECTED,
            data={
                "connection_id": connection_id,
                "user_id": str(user_id),
                "message": "WebSocket connection established",
            },
        ))

        # 消息处理循环
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_text()
                message = json.loads(data)

                logger.debug(f"[WebSocket] Received message from {connection_id}: {message}")

                # 处理心跳
                if message.get("type") == "ping":
                    await connection.send({"type": "pong", "timestamp": message.get("timestamp")})
                    ws_manager.update_heartbeat(connection_id)
                    continue

                # 处理订阅请求
                action = message.get("action")
                job_id_str = message.get("job_id")

                if action == "subscribe" and job_id_str:
                    try:
                        job_id = UUID(job_id_str)
                        success = await ws_manager.subscribe_job(connection_id, job_id)

                        if success:
                            await connection.send(build_event(
                                event_type=WebSocketEventType.SUBSCRIBED,
                                data={
                                    "job_id": job_id_str,
                                    "message": f"Subscribed to job {job_id_str}",
                                },
                            ))
                        else:
                            await connection.send(build_error_event(
                                code="SUBSCRIBE_FAILED",
                                message="Failed to subscribe to job",
                            ))
                    except ValueError:
                        await connection.send(build_error_event(
                            code="INVALID_JOB_ID",
                            message="Invalid job ID format",
                        ))

                elif action == "unsubscribe" and job_id_str:
                    try:
                        job_id = UUID(job_id_str)
                        success = await ws_manager.unsubscribe_job(connection_id, job_id)

                        if success:
                            await connection.send(build_event(
                                event_type=WebSocketEventType.UNSUBSCRIBED,
                                data={
                                    "job_id": job_id_str,
                                    "message": f"Unsubscribed from job {job_id_str}",
                                },
                            ))
                        else:
                            await connection.send(build_error_event(
                                code="UNSUBSCRIBE_FAILED",
                                message="Failed to unsubscribe from job",
                            ))
                    except ValueError:
                        await connection.send(build_error_event(
                            code="INVALID_JOB_ID",
                            message="Invalid job ID format",
                        ))

                else:
                    await connection.send(build_error_event(
                        code="INVALID_MESSAGE",
                        message="Invalid message format",
                    ))

            except WebSocketDisconnect:
                logger.info(f"[WebSocket] Client {connection_id} disconnected")
                break
            except json.JSONDecodeError:
                await connection.send(build_error_event(
                    code="INVALID_JSON",
                    message="Invalid JSON format",
                ))
            except Exception as e:
                logger.error(f"[WebSocket] Error processing message: {e}")
                await connection.send(build_error_event(
                    code="INTERNAL_ERROR",
                    message=str(e),
                ))

    except Exception as e:
        logger.error(f"[WebSocket] Connection error: {e}")
    finally:
        # 清理连接
        ws_manager.disconnect(connection_id)
        logger.info(f"[WebSocket] Connection {connection_id} cleaned up")


# 事件发布辅助函数（供其他模块调用）

async def publish_job_progress(
    job_id: UUID,
    progress: int,
    stage: str = None,
    message: str = None
) -> int:
    """发布任务进度事件"""
    from filmdub.apps.web.backend.websocket.event_types import build_progress_event

    event = build_progress_event(job_id, progress, stage, message)
    sent_count = await ws_manager.broadcast_to_job(job_id, event)
    logger.debug(f"[WebSocket] Published progress event for job {job_id} to {sent_count} subscribers")
    return sent_count


async def publish_job_stage(
    job_id: UUID,
    stage: str,
    previous_stage: str = None,
    message: str = None
) -> int:
    """发布任务阶段事件"""
    from filmdub.apps.web.backend.websocket.event_types import build_stage_event

    event = build_stage_event(job_id, stage, previous_stage, message)
    sent_count = await ws_manager.broadcast_to_job(job_id, event)
    logger.debug(f"[WebSocket] Published stage event for job {job_id} to {sent_count} subscribers")
    return sent_count


async def publish_job_completed(
    job_id: UUID,
    status: str,
    duration: float = None,
    output_artifacts: list[str] = None
) -> int:
    """发布任务完成事件"""
    from filmdub.apps.web.backend.websocket.event_types import build_completed_event

    event = build_completed_event(job_id, status, duration, output_artifacts)
    sent_count = await ws_manager.broadcast_to_job(job_id, event)
    logger.info(f"[WebSocket] Published completed event for job {job_id} to {sent_count} subscribers")
    return sent_count


async def publish_job_failed(
    job_id: UUID,
    error_message: str,
    error_stack: str = None,
    stage: str = None
) -> int:
    """发布任务失败事件"""
    from filmdub.apps.web.backend.websocket.event_types import build_failed_event

    event = build_failed_event(job_id, error_message, error_stack, stage)
    sent_count = await ws_manager.broadcast_to_job(job_id, event)
    logger.warning(f"[WebSocket] Published failed event for job {job_id} to {sent_count} subscribers")
    return sent_count


async def publish_job_created(
    job_id: UUID,
    job_name: str,
    project_id: UUID = None,
    user_id: UUID = None,
) -> int:
    """发布任务创建事件（全局广播给该用户的所有连接，Dashboard/任务列表实时刷新）"""
    from filmdub.apps.web.backend.websocket.event_types import build_job_created_event

    event = build_job_created_event(job_id, job_name, project_id)
    if user_id:
        sent_count = await ws_manager.broadcast_to_user(user_id, event)
    else:
        sent_count = await ws_manager.broadcast_to_job(job_id, event)
    logger.info(f"[WebSocket] Published created event for job {job_id} to {sent_count} connections")
    return sent_count


async def publish_job_status_changed(
    job_id: UUID,
    new_status: str,
    old_status: str = None,
    user_id: UUID = None,
) -> int:
    """发布任务状态变更事件（全局广播给该用户的所有连接）"""
    from filmdub.apps.web.backend.websocket.event_types import build_status_changed_event

    event = build_status_changed_event(job_id, new_status, old_status)
    if user_id:
        sent_count = await ws_manager.broadcast_to_user(user_id, event)
    else:
        sent_count = await ws_manager.broadcast_to_job(job_id, event)
    logger.info(f"[WebSocket] Published status_changed event for job {job_id} -> {new_status} to {sent_count} connections")
    return sent_count


# 启动和停止 WebSocket 管理器
async def start_websocket_manager():
    """启动 WebSocket 管理器"""
    await ws_manager.start()


async def stop_websocket_manager():
    """停止 WebSocket 管理器"""
    await ws_manager.stop()
