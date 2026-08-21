"""
Ticket 015 WebSocket 实时通信测试

覆盖：
- ConnectionManager：连接/断开/订阅/广播/个人消息/频道定向广播
- 认证：Worker/User token 验证、无效 token 拒绝
- 消息处理：subscribe/unsubscribe/ping
- 便捷广播函数：作业进度、系统事件、用户通知
"""
import json

import pytest

from filmdub.apps.api.websocket.manager import ConnectionManager
from filmdub.apps.api.websocket.handler import (
    _authenticate,
    handle_message,
    broadcast_job_progress,
    broadcast_system_event,
    notify_user,
)
from filmdub.orchestrator.jwt_handler import JWTHandler


class _FakeWebSocket:
    """模拟 FastAPI WebSocket。"""

    def __init__(self):
        self.accepted = False
        self.sent: list = []
        self.closed: list = []
        self.incoming: list = []

    async def accept(self):
        self.accepted = True

    async def send_text(self, text: str):
        self.sent.append(json.loads(text))

    async def receive_text(self) -> str:
        if not self.incoming:
            raise Exception("no more messages")
        return self.incoming.pop(0)

    async def close(self, code=1000, reason=None):
        self.closed.append((code, reason))


# ==================== ConnectionManager ====================


@pytest.mark.asyncio
async def test_connect_disconnect():
    manager = ConnectionManager()
    ws = _FakeWebSocket()
    await manager.connect(ws, "conn-1", "user-1")

    assert ws.accepted is True
    assert manager.get_connection_count() == 1
    assert manager.get_user_count() == 1

    manager.disconnect("conn-1", "user-1")
    assert manager.get_connection_count() == 0
    assert manager.get_user_count() == 0


@pytest.mark.asyncio
async def test_send_personal_message():
    manager = ConnectionManager()
    ws1 = _FakeWebSocket()
    ws2 = _FakeWebSocket()
    await manager.connect(ws1, "conn-1", "user-1")
    await manager.connect(ws2, "conn-2", "user-2")

    await manager.send_personal_message({"type": "notification", "msg": "hi"}, "user-1")

    assert len(ws1.sent) == 1
    assert ws1.sent[0]["msg"] == "hi"
    assert ws2.sent == []


@pytest.mark.asyncio
async def test_broadcast_channel_filtering():
    manager = ConnectionManager()
    ws_a = _FakeWebSocket()
    ws_b = _FakeWebSocket()
    await manager.connect(ws_a, "conn-a", "user-a")
    await manager.connect(ws_b, "conn-b", "user-b")

    # 只有订阅了 channel-x 的连接收到定向广播
    manager.subscribe("conn-a", "channel-x")
    await manager.broadcast({"type": "event", "data": 1}, channel="channel-x")

    assert len(ws_a.sent) == 1
    assert ws_a.sent[0]["type"] == "event"
    assert ws_b.sent == []

    # 无频道 → 广播给所有连接
    await manager.broadcast({"type": "global"})
    assert len(ws_b.sent) == 1
    assert ws_b.sent[0]["type"] == "global"


@pytest.mark.asyncio
async def test_subscribe_unsubscribe():
    manager = ConnectionManager()
    await manager.connect(_FakeWebSocket(), "conn-1")

    manager.subscribe("conn-1", "channel-y")
    assert manager.channel_subscriptions["channel-y"] == {"conn-1"}

    manager.unsubscribe("conn-1", "channel-y")
    assert "channel-y" not in manager.channel_subscriptions


@pytest.mark.asyncio
async def test_disconnect_cleans_subscriptions():
    manager = ConnectionManager()
    await manager.connect(_FakeWebSocket(), "conn-1")
    manager.subscribe("conn-1", "channel-z")
    manager.disconnect("conn-1")
    assert "channel-z" not in manager.channel_subscriptions


# ==================== 认证 ====================


def test_authenticate_worker_token():
    jwt = JWTHandler()  # 默认 secret，与 handler 运行时一致
    token = jwt.create_token("worker-123")
    assert _authenticate(token) == "worker-123"


def test_authenticate_user_token():
    jwt = JWTHandler()
    token = jwt.encode({"type": "user", "user_id": "u-42", "exp": 2**31})
    assert _authenticate(token) == "u-42"


def test_authenticate_invalid_token():
    assert _authenticate("garbage-token") is None
    assert _authenticate(None) is None


def test_authenticate_expired_token():
    jwt = JWTHandler()
    token = jwt.encode({"type": "user", "user_id": "u-1", "exp": 0})
    assert _authenticate(token) is None


# ==================== 消息处理 ====================


@pytest.mark.asyncio
async def test_handle_message_ping():
    manager = ConnectionManager()
    ws = _FakeWebSocket()
    await manager.connect(ws, "conn-1")

    await handle_message("conn-1", "user-1", {"type": "ping", "timestamp": 123}, manager=manager)
    assert ws.sent[-1]["type"] == "pong"
    assert ws.sent[-1]["timestamp"] == 123


@pytest.mark.asyncio
async def test_handle_message_subscribe():
    manager = ConnectionManager()
    await manager.connect(_FakeWebSocket(), "conn-1")

    await handle_message("conn-1", "user-1", {"type": "subscribe", "channel": "project:p1"}, manager=manager)
    assert manager.channel_subscriptions["project:p1"] == {"conn-1"}

    await handle_message("conn-1", "user-1", {"type": "unsubscribe", "channel": "project:p1"}, manager=manager)
    assert "project:p1" not in manager.channel_subscriptions


# ==================== 便捷广播 ====================


@pytest.mark.asyncio
async def test_broadcast_job_progress():
    manager = ConnectionManager()
    ws = _FakeWebSocket()
    await manager.connect(ws, "conn-1")
    manager.subscribe("conn-1", "project:p-9")

    await broadcast_job_progress("job-1", "p-9", 50.0, "running", "渲染中", manager=manager)
    msg = ws.sent[-1]
    assert msg["type"] == "job_progress"
    assert msg["job_id"] == "job-1"
    assert msg["progress"] == 50.0
    assert msg["project_id"] == "p-9"


@pytest.mark.asyncio
async def test_broadcast_system_event():
    manager = ConnectionManager()
    ws = _FakeWebSocket()
    await manager.connect(ws, "conn-1")

    await broadcast_system_event("worker_offline", {"worker_id": "w1"}, manager=manager)
    msg = ws.sent[-1]
    assert msg["type"] == "system_event"
    assert msg["event_type"] == "worker_offline"
    assert msg["data"]["worker_id"] == "w1"


@pytest.mark.asyncio
async def test_notify_user():
    manager = ConnectionManager()
    ws = _FakeWebSocket()
    await manager.connect(ws, "conn-1", "user-77")

    await notify_user("user-77", "job_done", "作业完成", manager=manager)
    msg = ws.sent[-1]
    assert msg["type"] == "notification"
    assert msg["message"] == "作业完成"
