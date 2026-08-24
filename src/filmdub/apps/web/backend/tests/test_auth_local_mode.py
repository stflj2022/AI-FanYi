"""本地免登录模式测试（AUTH_DISABLED=true，ticket: 免登录）

覆盖：
- 本地模式：无 Token 访问受保护接口返回本地默认用户（local, is_admin）
- 本地模式：管理员接口放行
- health 上报 auth_disabled
- 非本地模式：无 Token 仍返回 401（保持既有认证行为）
"""
import pytest
from httpx import AsyncClient, ASGITransport

from filmdub.apps.web.backend.main import app
from filmdub.core.config import settings
from filmdub.core import orchestrator_db


@pytest.fixture
async def local_client(db_session):
    """使用 sqlite 内存库 + 覆盖 get_db 的客户端"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[orchestrator_db.get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_local_mode_me_without_token(local_client, monkeypatch):
    """本地模式：无 Token 访问 /auth/me 返回本地默认用户"""
    monkeypatch.setattr(settings, "auth_disabled", True)
    resp = await local_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "local"
    assert data["is_admin"] is True
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_local_mode_projects_without_token(local_client, monkeypatch):
    """本地模式：无 Token 访问业务接口返回 200"""
    monkeypatch.setattr(settings, "auth_disabled", True)
    resp = await local_client.get("/api/v1/projects")
    assert resp.status_code == 200
    # 返回分页结构（items 或 list 均可），重点是免认证放行
    data = resp.json()
    assert isinstance(data, (list, dict))


@pytest.mark.asyncio
async def test_local_mode_admin_endpoint(local_client, monkeypatch):
    """本地模式：管理员接口（/auth/users）直接放行"""
    monkeypatch.setattr(settings, "auth_disabled", True)
    resp = await local_client.get("/api/v1/auth/users")
    assert resp.status_code == 200
    # 列表中应包含自动创建的 local 用户
    usernames = [u.get("username") for u in resp.json()]
    assert "local" in usernames


@pytest.mark.asyncio
async def test_local_mode_settings(local_client, monkeypatch):
    """本地模式：settings 接口无 Token 可访问"""
    monkeypatch.setattr(settings, "auth_disabled", True)
    resp = await local_client.get("/api/v1/settings")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_reports_auth_disabled(local_client, monkeypatch):
    """health 接口上报 auth_disabled 状态（供前端检测）"""
    monkeypatch.setattr(settings, "auth_disabled", True)
    resp = await local_client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["auth_disabled"] is True


@pytest.mark.asyncio
async def test_health_reports_auth_enabled(local_client, monkeypatch):
    """非本地模式：health 上报 auth_disabled=False"""
    monkeypatch.setattr(settings, "auth_disabled", False)
    resp = await local_client.get("/api/v1/health")
    assert resp.json()["auth_disabled"] is False


@pytest.mark.asyncio
async def test_non_local_mode_still_requires_token(local_client, monkeypatch):
    """非本地模式：无 Token 访问 /auth/me 仍返回 401（既有行为不变）"""
    monkeypatch.setattr(settings, "auth_disabled", False)
    resp = await local_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ws_local_mode_user_id_matches_db(db_session, monkeypatch):
    """本地模式：WebSocket 返回的 user_id 与 DB 中 local 用户 id 一致（保证实时事件匹配）"""
    from uuid import UUID
    from filmdub.apps.web.backend.websocket.events import get_current_user_ws
    from filmdub.apps.web.backend.services.auth_service import AuthService

    monkeypatch.setattr(settings, "auth_disabled", True)

    class FakeWS:
        async def close(self, code=None, reason=None):
            pass

    uid = await get_current_user_ws(FakeWS(), token=None, db=db_session)
    assert isinstance(uid, UUID)

    local_user = await AuthService.get_user_by_username(db_session, "local")
    assert local_user is not None
    assert uid == local_user.id
