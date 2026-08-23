"""WebSocket 相关测试"""
import pytest
import json
from uuid import uuid4
from datetime import datetime

from filmdub.apps.web.backend.websocket.manager import WebSocketManager, WebSocketConnection
from filmdub.apps.web.backend.websocket.event_types import (
    WebSocketEventType,
    build_event,
    build_progress_event,
    build_stage_event,
    build_completed_event,
    build_failed_event,
)


@pytest.fixture
def ws_manager():
    """创建 WebSocket 管理器"""
    manager = WebSocketManager(heartbeat_interval=1, heartbeat_timeout=2)
    yield manager
    # 清理


class TestWebSocketManager:
    """WebSocket 管理器测试"""

    @pytest.mark.asyncio
    async def test_connection_lifecycle(self, ws_manager):
        """测试连接生命周期"""
        # 创建模拟的 WebSocket 连接
        from unittest.mock import AsyncMock, MagicMock

        mock_websocket = MagicMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.close = AsyncMock()

        user_id = uuid4()
        connection_id = "test-connection-1"

        # 建立连接
        connection = await ws_manager.connect(mock_websocket, user_id, connection_id)
        assert connection.user_id == user_id
        assert connection.is_alive
        assert ws_manager.get_connection_count() == 1

        # 断开连接
        ws_manager.disconnect(connection_id)
        assert ws_manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe_job(self, ws_manager):
        """测试任务订阅和取消订阅"""
        from unittest.mock import AsyncMock, MagicMock

        mock_websocket = MagicMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_json = AsyncMock()

        user_id = uuid4()
        connection_id = "test-connection-2"
        job_id = uuid4()

        # 建立连接
        await ws_manager.connect(mock_websocket, user_id, connection_id)

        # 订阅任务
        success = await ws_manager.subscribe_job(connection_id, job_id)
        assert success
        assert ws_manager.get_subscriber_count(job_id) == 1

        # 取消订阅
        success = await ws_manager.unsubscribe_job(connection_id, job_id)
        assert success
        assert ws_manager.get_subscriber_count(job_id) == 0

        # 清理
        ws_manager.disconnect(connection_id)

    @pytest.mark.asyncio
    async def test_broadcast_to_job(self, ws_manager):
        """测试向任务订阅者广播"""
        from unittest.mock import AsyncMock, MagicMock

        # 创建多个连接
        connections = []
        for i in range(3):
            mock_ws = MagicMock()
            mock_ws.accept = AsyncMock()
            mock_ws.send_json = AsyncMock()
            connections.append(mock_ws)

        job_id = uuid4()
        connection_ids = []

        # 建立连接并订阅
        for i, mock_ws in enumerate(connections):
            conn_id = f"test-connection-{i}"
            user_id = uuid4()
            await ws_manager.connect(mock_ws, user_id, conn_id)
            await ws_manager.subscribe_job(conn_id, job_id)
            connection_ids.append(conn_id)

        # 广播事件
        event_data = build_progress_event(job_id, 50, "processing", "Test message")
        sent_count = await ws_manager.broadcast_to_job(job_id, event_data)

        assert sent_count == 3

        # 验证每个连接都收到了消息
        for mock_ws in connections:
            mock_ws.send_json.assert_called_once()

        # 清理
        for conn_id in connection_ids:
            ws_manager.disconnect(conn_id)

    @pytest.mark.asyncio
    async def test_heartbeat_update(self, ws_manager):
        """测试心跳更新"""
        from unittest.mock import AsyncMock, MagicMock

        mock_websocket = MagicMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_json = AsyncMock()

        user_id = uuid4()
        connection_id = "test-connection-3"

        # 建立连接
        await ws_manager.connect(mock_websocket, user_id, connection_id)

        # 更新心跳
        success = ws_manager.update_heartbeat(connection_id)
        assert success

        # 验证心跳时间已更新
        connection = ws_manager.active_connections[connection_id]
        assert (datetime.utcnow() - connection.last_heartbeat).total_seconds() < 1

        # 清理
        ws_manager.disconnect(connection_id)


class TestEventBuilders:
    """事件构建器测试"""

    def test_build_event(self):
        """测试基础事件构建"""
        event = build_event(
            event_type=WebSocketEventType.JOB_CREATED,
            data={"job_id": str(uuid4())},
        )

        assert event["event_type"] == "job.created"
        assert "timestamp" in event
        assert "data" in event

    def test_build_progress_event(self):
        """测试进度事件构建"""
        job_id = uuid4()
        event = build_progress_event(job_id, 50, "processing", "Test message")

        assert event["event_type"] == "job.progress"
        assert event["job_id"] == str(job_id)
        assert event["data"]["progress"] == 50
        assert event["data"]["stage"] == "processing"
        assert event["data"]["message"] == "Test message"

    def test_build_stage_event(self):
        """测试阶段事件构建"""
        job_id = uuid4()
        event = build_stage_event(job_id, "encoding", "processing", "Starting encoding")

        assert event["event_type"] == "job.stage"
        assert event["job_id"] == str(job_id)
        assert event["data"]["stage"] == "encoding"
        assert event["data"]["previous_stage"] == "processing"
        assert event["data"]["message"] == "Starting encoding"

    def test_build_completed_event(self):
        """测试完成事件构建"""
        job_id = uuid4()
        event = build_completed_event(job_id, "completed", 120.5, ["artifact1", "artifact2"])

        assert event["event_type"] == "job.completed"
        assert event["job_id"] == str(job_id)
        assert event["data"]["status"] == "completed"
        assert event["data"]["duration"] == 120.5
        assert len(event["data"]["output_artifacts"]) == 2

    def test_build_failed_event(self):
        """测试失败事件构建"""
        job_id = uuid4()
        error_stack = "Traceback (most recent call last):\n  ..."
        event = build_failed_event(job_id, "Test error", error_stack, "processing")

        assert event["event_type"] == "job.failed"
        assert event["job_id"] == str(job_id)
        assert event["data"]["error_message"] == "Test error"
        assert event["data"]["error_stack"] == error_stack
        assert event["data"]["stage"] == "processing"


class TestWebSocketIntegration:
    """WebSocket 集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_message_flow(self, ws_manager):
        """测试端到端消息流程"""
        from unittest.mock import AsyncMock, MagicMock

        # 创建连接
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        user_id = uuid4()
        connection_id = "test-connection-4"
        job_id = uuid4()

        # 建立连接并订阅
        await ws_manager.connect(mock_ws, user_id, connection_id)
        await ws_manager.subscribe_job(connection_id, job_id)

        # 发送进度事件
        progress_event = build_progress_event(job_id, 30, "uploading", "Uploading video...")
        await ws_manager.broadcast_to_job(job_id, progress_event)

        # 发送阶段事件
        stage_event = build_stage_event(job_id, "processing", "uploading", "Starting processing")
        await ws_manager.broadcast_to_job(job_id, stage_event)

        # 发送完成事件
        completed_event = build_completed_event(job_id, "completed", 60.0, ["output.mp4"])
        await ws_manager.broadcast_to_job(job_id, completed_event)

        # 验证发送了 3 个消息
        assert mock_ws.send_json.call_count == 3

        # 清理
        ws_manager.disconnect(connection_id)
