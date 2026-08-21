"""
WebSocket 处理器

处理 WebSocket 连接和消息
"""
import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import logging

logger = logging.getLogger(__name__)

from .manager import ConnectionManager

# 创建全局连接管理器
manager = ConnectionManager()

router = APIRouter()


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
        token: 认证 Token
        project_id: 项目 ID（可选）
    """
    connection_id = str(uuid.uuid4())

    # TODO: 验证 Token
    user_id = "user_1"  # 临时用户 ID

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
    message: Dict[str, Any]
):
    """
    处理收到的消息

    Args:
        connection_id: 连接 ID
        user_id: 用户 ID
        message: 消息内容
    """
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
    message: Optional[str] = None
):
    """
    广播作业进度

    Args:
        job_id: 作业 ID
        project_id: 项目 ID
        progress: 进度 (0-100)
        status: 状态
        message: 消息（可选）
    """
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
    data: Dict[str, Any]
):
    """
    广播系统事件

    Args:
        event_type: 事件类型
        data: 事件数据
    """
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
    data: Optional[Dict[str, Any]] = None
):
    """
    通知用户

    Args:
        user_id: 用户 ID
        notification_type: 通知类型
        message: 消息
        data: 附加数据（可选）
    """
    await manager.send_personal_message({
        "type": "notification",
        "notification_type": notification_type,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }, user_id)
