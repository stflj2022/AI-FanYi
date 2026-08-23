"""Web Backend 健康检查测试"""
import pytest
from fastapi.testclient import TestClient

from filmdub.apps.web.backend.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


def test_health_check(client):
    """测试健康检查端点"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "web-backend"
    assert "version" in data


def test_root_endpoint(client):
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "AI-FanYi Web Backend"
    assert data["status"] == "running"
