"""
WebSocket 连接管理器

管理 WebSocket 连接、消息广播和频道订阅
"""
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)
import json


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        """初始化管理器"""
        # 活跃连接: {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}

        # 用户连接: {user_id: Set[connection_id]}
        self.user_connections: Dict[str, Set[str]] = {}

        # 频道订阅: {channel: Set[connection_id]}
        self.channel_subscriptions: Dict[str, Set[str]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: Optional[str] = None
    ):
        """
        建立连接

        Args:
            websocket: WebSocket 连接
            connection_id: 连接 ID
            user_id: 用户 ID（可选）
        """
        await websocket.accept()
        self.active_connections[connection_id] = websocket

        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)

        logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")

    def disconnect(self, connection_id: str, user_id: Optional[str] = None):
        """
        断开连接

        Args:
            connection_id: 连接 ID
            user_id: 用户 ID（可选）
        """
        # 移除活跃连接
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        # 移除用户连接
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        # 移除频道订阅
        for channel, subscribers in self.channel_subscriptions.items():
            subscribers.discard(connection_id)
            if not subscribers:
                del self.channel_subscriptions[channel]

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def send_personal_message(
        self,
        message: Dict[str, Any],
        user_id: str
    ):
        """
        发送个人消息

        Args:
            message: 消息内容
            user_id: 用户 ID
        """
        if user_id not in self.user_connections:
            return

        message_str = json.dumps(message)

        for connection_id in self.user_connections[user_id]:
            if connection_id in self.active_connections:
                try:
                    await self.active_connections[connection_id].send_text(message_str)
                except Exception as e:
                    logger.error(f"Failed to send message to {connection_id}: {e}")

    async def broadcast(
        self,
        message: Dict[str, Any],
        channel: Optional[str] = None
    ):
        """
        广播消息

        Args:
            message: 消息内容
            channel: 频道名称（可选）
        """
        message_str = json.dumps(message)

        # 确定目标连接
        if channel:
            # 发送给特定频道的订阅者
            targets = self.channel_subscriptions.get(channel, set())
        else:
            # 发送给所有连接
            targets = set(self.active_connections.keys())

        for connection_id in targets:
            if connection_id in self.active_connections:
                try:
                    await self.active_connections[connection_id].send_text(message_str)
                except Exception as e:
                    logger.error(f"Failed to broadcast to {connection_id}: {e}")

    async def send_to_connection(
        self,
        message: Dict[str, Any],
        connection_id: str
    ):
        """
        发送消息到特定连接

        Args:
            message: 消息内容
            connection_id: 连接 ID
        """
        if connection_id not in self.active_connections:
            return

        message_str = json.dumps(message)

        try:
            await self.active_connections[connection_id].send_text(message_str)
        except Exception as e:
            logger.error(f"Failed to send to {connection_id}: {e}")

    def subscribe(self, connection_id: str, channel: str):
        """
        订阅频道

        Args:
            connection_id: 连接 ID
            channel: 频道名称
        """
        if channel not in self.channel_subscriptions:
            self.channel_subscriptions[channel] = set()

        self.channel_subscriptions[channel].add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to {channel}")

    def unsubscribe(self, connection_id: str, channel: str):
        """
        取消订阅频道

        Args:
            connection_id: 连接 ID
            channel: 频道名称
        """
        if channel in self.channel_subscriptions:
            self.channel_subscriptions[channel].discard(connection_id)

            if not self.channel_subscriptions[channel]:
                del self.channel_subscriptions[channel]

        logger.info(f"Connection {connection_id} unsubscribed from {channel}")

    def get_connection_count(self) -> int:
        """获取活跃连接数"""
        return len(self.active_connections)

    def get_user_count(self) -> int:
        """获取用户数"""
        return len(self.user_connections)
