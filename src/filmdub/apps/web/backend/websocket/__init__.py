"""WebSocket 模块"""

from filmdub.apps.web.backend.websocket.manager import ws_manager, WebSocketManager
from filmdub.apps.web.backend.websocket.event_types import (
    WebSocketEventType,
    build_event,
    build_progress_event,
    build_stage_event,
    build_completed_event,
    build_failed_event,
    build_error_event,
)
from filmdub.apps.web.backend.websocket.events import (
    publish_job_progress,
    publish_job_stage,
    publish_job_completed,
    publish_job_failed,
)

__all__ = [
    "ws_manager",
    "WebSocketManager",
    "WebSocketEventType",
    "build_event",
    "build_progress_event",
    "build_stage_event",
    "build_completed_event",
    "build_failed_event",
    "build_error_event",
    "publish_job_progress",
    "publish_job_stage",
    "publish_job_completed",
    "publish_job_failed",
]
