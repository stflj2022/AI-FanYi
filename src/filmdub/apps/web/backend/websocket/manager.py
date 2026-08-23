"""WebSocket 连接管理器

管理所有活动的 WebSocket 连接，支持订阅/取消订阅、心跳检测等功能
"""
import json
import asyncio
from typing import Dict, Set, Optional, Any
from datetime import datetime, timedelta
from uuid import UUID
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect


@dataclass
class WebSocketConnection:
    """WebSocket 连接信息"""
    websocket: WebSocket
    user_id: UUID
    subscribed_jobs: Set[UUID] = field(default_factory=set)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    is_alive: bool = True

    async def send(self, data: Dict[str, Any]) -> bool:
        """发送消息到客户端"""
        try:
            await self.websocket.send_json(data)
            return True
        except Exception:
            self.is_alive = False
            return False

    async def close(self) -> None:
        """关闭连接"""
        try:
            await self.websocket.close()
        except Exception:
            pass
        self.is_alive = False


class WebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self, heartbeat_interval: int = 30, heartbeat_timeout: int = 90):
        self.active_connections: Dict[str, WebSocketConnection] = {}
        self.job_subscribers: Dict[UUID, Set[str]] = {}  # job_id -> connection_ids
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._started = False

    async def connect(self, websocket: WebSocket, user_id: UUID, connection_id: str) -> WebSocketConnection:
        """建立新的 WebSocket 连接"""
        await websocket.accept()

        connection = WebSocketConnection(
            websocket=websocket,
            user_id=user_id,
            last_heartbeat=datetime.utcnow(),
            is_alive=True
        )

        self.active_connections[connection_id] = connection
        print(f"[WebSocket] Connection {connection_id} established for user {user_id}")

        return connection

    def disconnect(self, connection_id: str) -> None:
        """断开 WebSocket 连接"""
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]

            # 从所有 job 订阅中移除
            for job_id in connection.subscribed_jobs:
                if job_id in self.job_subscribers:
                    self.job_subscribers[job_id].discard(connection_id)
                    if not self.job_subscribers[job_id]:
                        del self.job_subscribers[job_id]

            del self.active_connections[connection_id]
            print(f"[WebSocket] Connection {connection_id} disconnected")

    async def subscribe_job(self, connection_id: str, job_id: UUID) -> bool:
        """订阅任务事件"""
        if connection_id not in self.active_connections:
            return False

        connection = self.active_connections[connection_id]

        if job_id not in self.job_subscribers:
            self.job_subscribers[job_id] = set()

        self.job_subscribers[job_id].add(connection_id)
        connection.subscribed_jobs.add(job_id)

        print(f"[WebSocket] Connection {connection_id} subscribed to job {job_id}")
        return True

    async def unsubscribe_job(self, connection_id: str, job_id: UUID) -> bool:
        """取消订阅任务事件"""
        if connection_id not in self.active_connections:
            return False

        connection = self.active_connections[connection_id]

        if job_id in self.job_subscribers:
            self.job_subscribers[job_id].discard(connection_id)
            if not self.job_subscribers[job_id]:
                del self.job_subscribers[job_id]

        connection.subscribed_jobs.discard(job_id)

        print(f"[WebSocket] Connection {connection_id} unsubscribed from job {job_id}")
        return True

    async def broadcast_to_job(self, job_id: UUID, event_data: Dict[str, Any]) -> int:
        """向订阅指定任务的所有客户端广播事件"""
        if job_id not in self.job_subscribers:
            return 0

        subscribers = self.job_subscribers[job_id].copy()
        sent_count = 0

        for conn_id in subscribers:
            if conn_id in self.active_connections:
                connection = self.active_connections[conn_id]
                success = await connection.send(event_data)
                if success:
                    sent_count += 1
                else:
                    # 连接已断开，清理
                    self.disconnect(conn_id)

        return sent_count

    async def broadcast_to_user(self, user_id: UUID, event_data: Dict[str, Any]) -> int:
        """向指定用户的所有连接广播事件"""
        sent_count = 0

        for conn_id, connection in list(self.active_connections.items()):
            if connection.user_id == user_id:
                success = await connection.send(event_data)
                if success:
                    sent_count += 1
                else:
                    self.disconnect(conn_id)

        return sent_count

    async def send_to_connection(self, connection_id: str, event_data: Dict[str, Any]) -> bool:
        """向指定连接发送事件"""
        if connection_id not in self.active_connections:
            return False

        connection = self.active_connections[connection_id]
        success = await connection.send(event_data)

        if not success:
            self.disconnect(connection_id)

        return success

    def update_heartbeat(self, connection_id: str) -> bool:
        """更新心跳时间"""
        if connection_id not in self.active_connections:
            return False

        self.active_connections[connection_id].last_heartbeat = datetime.utcnow()
        return True

    async def _heartbeat_checker(self) -> None:
        """心跳检测任务"""
        while self._started:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                now = datetime.utcnow()

                for conn_id, connection in list(self.active_connections.items()):
                    # 检查心跳超时
                    if (now - connection.last_heartbeat).total_seconds() > self.heartbeat_timeout:
                        print(f"[WebSocket] Connection {conn_id} heartbeat timeout, disconnecting...")
                        await connection.close()
                        self.disconnect(conn_id)
                    else:
                        # 发送心跳 ping
                        try:
                            await connection.websocket.send_json({"type": "ping"})
                        except Exception:
                            connection.is_alive = False
                            self.disconnect(conn_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[WebSocket] Heartbeat checker error: {e}")

    async def start(self) -> None:
        """启动心跳检测"""
        if not self._started:
            self._started = True
            self._heartbeat_task = asyncio.create_task(self._heartbeat_checker())
            print("[WebSocket] Heartbeat checker started")

    async def stop(self) -> None:
        """停止心跳检测并关闭所有连接"""
        self._started = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # 关闭所有连接
        for conn_id, connection in list(self.active_connections.items()):
            await connection.close()
            self.disconnect(conn_id)

        print("[WebSocket] All connections closed")

    def get_connection_count(self) -> int:
        """获取活动连接数"""
        return len(self.active_connections)

    def get_subscriber_count(self, job_id: UUID) -> int:
        """获取任务的订阅者数量"""
        if job_id not in self.job_subscribers:
            return 0
        return len(self.job_subscribers[job_id])


# 全局 WebSocket 管理器实例
ws_manager = WebSocketManager()
