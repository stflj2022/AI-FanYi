"""
WebSocket 处理器

处理 WebSocket 连接和消息
"""
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import logging

logger = logging.getLogger(__name__)

from .manager import ConnectionManager
from filmdub.orchestrator.jwt_handler import JWTHandler

# 创建全局连接管理器
manager = ConnectionManager()

router = APIRouter()


def _authenticate(token: Optional[str]) -> Optional[str]:
    """
    认证 WebSocket 连接：验证 JWT Token，返回用户/Worker ID。

    支持两种 token：
    - Worker token（type=worker）：返回 worker_id
    - 普通用户 token（type=user）：返回 user_id
    无效 token 返回 None。
    """
    if not token:
        return None
    jwt = JWTHandler()
    try:
        payload = jwt.decode(token)
    except Exception:
        return None
    if payload.get("type") == "worker":
        return payload.get("worker_id")
    if payload.get("type") == "user":
        return payload.get("user_id")
    return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None)
):
    """
    WebSocket 端点

    Args:
        websocket: WebSocket 连接
        token: 认证 Token（可选，匿名连接允许只读订阅）
        project_id: 项目 ID（可选）
    """
    connection_id = str(uuid.uuid4())

    # 验证 Token（提供 token 但无效时拒绝连接）
    user_id = _authenticate(token)
    if token and user_id is None:
        await websocket.close(code=4401, reason="Invalid or expired token")
        logger.warning(f"WebSocket rejected: invalid token (connection {connection_id})")
        return

    try:
        # 建立连接
        await manager.connect(websocket, connection_id, user_id)

        # 订阅项目频道
        if project_id:
            manager.subscribe(connection_id, f"project:{project_id}")

        # 发送欢迎消息
        await manager.send_to_connection({
            "type": "connected",
            "connection_id": connection_id,
            "message": "WebSocket connected successfully"
        }, connection_id)

        # 消息循环
        while True:
            # 接收消息
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                await handle_message(connection_id, user_id, message)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from {connection_id}: {data}")
                await manager.send_to_connection({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, connection_id)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # 断开连接
        manager.disconnect(connection_id, user_id)


async def handle_message(
    connection_id: str,
    user_id: str,
    message: Dict[str, Any],
    manager: Optional[ConnectionManager] = None
):
    """
    处理收到的消息

    Args:
        connection_id: 连接 ID
        user_id: 用户 ID
        message: 消息内容
        manager: 连接管理器（默认使用全局实例，便于测试注入）
    """
    manager = manager or globals()["manager"]
    message_type = message.get("type")

    if message_type == "subscribe":
        # 订阅频道
        channel = message.get("channel")
        if channel:
            manager.subscribe(connection_id, channel)

    elif message_type == "unsubscribe":
        # 取消订阅频道
        channel = message.get("channel")
        if channel:
            manager.unsubscribe(connection_id, channel)

    elif message_type == "ping":
        # 心跳响应
        await manager.send_to_connection({
            "type": "pong",
            "timestamp": message.get("timestamp")
        }, connection_id)

    else:
        logger.warning(f"Unknown message type: {message_type}")


# 便捷函数
async def broadcast_job_progress(
    job_id: str,
    project_id: str,
    progress: float,
    status: str,
    message: Optional[str] = None,
    manager: Optional[ConnectionManager] = None
):
    """
    广播作业进度

    Args:
        job_id: 作业 ID
        project_id: 项目 ID
        progress: 进度 (0-100)
        status: 状态
        message: 消息（可选）
        manager: 连接管理器（默认使用全局实例）
    """
    manager = manager or globals()["manager"]
    await manager.broadcast({
        "type": "job_progress",
        "job_id": job_id,
        "project_id": project_id,
        "progress": progress,
        "status": status,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }, f"project:{project_id}")


async def broadcast_system_event(
    event_type: str,
    data: Dict[str, Any],
    manager: Optional[ConnectionManager] = None
):
    """
    广播系统事件

    Args:
        event_type: 事件类型
        data: 事件数据
        manager: 连接管理器（默认使用全局实例）
    """
    manager = manager or globals()["manager"]
    await manager.broadcast({
        "type": "system_event",
        "event_type": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_user(
    user_id: str,
    notification_type: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    manager: Optional[ConnectionManager] = None
):
    """
    通知用户

    Args:
        user_id: 用户 ID
        notification_type: 通知类型
        message: 消息
        data: 附加数据（可选）
        manager: 连接管理器（默认使用全局实例）
    """
    manager = manager or globals()["manager"]
    await manager.send_personal_message({
        "type": "notification",
        "notification_type": notification_type,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }, user_id)
