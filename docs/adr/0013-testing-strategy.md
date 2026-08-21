# ADR 0013: 测试策略设计

## 状态

设计中

## 上下文

影视AI配音平台是一个复杂的分布式系统，需要完善的测试策略确保系统质量。

## 测试金字塔

```
                    ┌─────────────────┐
                    │   E2E Tests     │  5%
                    │   (端到端)       │
                    ├─────────────────┤
                    │ Integration     │  15%
                    │   Tests         │  (集成测试)
                    ├─────────────────┤
                    │   Unit Tests    │  80%
                    │   (单元测试)     │
                    └─────────────────┘
```

## 测试分层

### 1. 单元测试

#### 目标
- 测试单个函数、类的行为
- 快速反馈（< 1s per test）
- 覆盖边界情况和错误路径

#### 工具
- **pytest**: 测试框架
- **pytest-asyncio**: 异步测试支持
- **pytest-cov**: 覆盖率报告
- **unittest.mock**: Mock 对象

#### 覆盖率目标
- **最低要求**: 70%
- **推荐目标**: 85%
- **理想目标**: 90%+

#### 示例

```python
# tests/unit/test_artifact_registry.py

import pytest
from src.artifacts.registry import ArtifactRegistry
from src.artifacts.storage import InMemoryStorage
from src.artifacts.models import ArtifactMetadata, ArtifactType
import uuid
from unittest.mock import Mock

@pytest.fixture
def artifact_registry():
    """创建 Artifact Registry 测试实例"""
    storage = InMemoryStorage()
    db = Mock()  # Mock 数据库
    return ArtifactRegistry(db, storage)

@pytest.fixture
def sample_metadata():
    """创建示例元数据"""
    return ArtifactMetadata(
        name="test_video.mp4",
        type=ArtifactType.VIDEO,
        project_id=uuid.uuid4(),
        mime_type="video/mp4",
        size_bytes=1024000
    )

@pytest.mark.asyncio
async def test_create_artifact(artifact_registry, sample_metadata):
    """测试创建 Artifact"""
    artifact_ref = await artifact_registry.create(sample_metadata)

    assert artifact_ref.metadata.name == "test_video.mp4"
    assert artifact_ref.metadata.type == ArtifactType.VIDEO
    assert artifact_ref.version == 1

@pytest.mark.asyncio
async def test_create_artifact_with_parent(artifact_registry, sample_metadata):
    """测试创建带父 Artifact 的 Artifact"""
    parent_id = uuid.uuid4()
    artifact_ref = await artifact_registry.create(
        sample_metadata,
        parent_artifact_id=parent_id
    )

    assert artifact_ref.version == 2  # 父版本 + 1

@pytest.mark.asyncio
async def test_upload_artifact(artifact_registry, sample_metadata):
    """测试上传 Artifact 数据"""
    import io

    artifact_ref = await artifact_registry.create(sample_metadata)
    data = io.BytesIO(b"test data")

    result = await artifact_registry.upload(artifact_ref.id, data)

    assert result.metadata.status == "ready"
    assert result.metadata.size_bytes == 9

@pytest.mark.asyncio
async def test_increment_ref_count(artifact_registry, sample_metadata):
    """测试增加引用计数"""
    artifact_ref = await artifact_registry.create(sample_metadata)
    await artifact_registry.upload(artifact_ref.id, io.BytesIO(b"data"))

    await artifact_registry.increment_ref(artifact_ref.id)

    # 验证引用计数增加
    artifact = await artifact_registry.get(artifact_ref.id)
    assert artifact.ref_count == 1

@pytest.mark.asyncio
async def test_nonexistent_artifact(artifact_registry):
    """测试获取不存在的 Artifact"""
    result = await artifact_registry.get(uuid.uuid4())
    assert result is None

@pytest.mark.asyncio
async def test_checksum_calculation(artifact_registry):
    """测试校验和计算"""
    test_data = b"test data"
    checksum = artifact_registry._calculate_checksum(io.BytesIO(test_data))

    assert checksum.startswith("sha256:")
    assert len(checksum) == 71  # "sha256:" + 64 hex chars
```

### 2. 集成测试

#### 目标
- 测试模块/组件之间的交互
- 测试数据库、缓存、外部服务集成
- 验证 API 端点

#### 工具
- **pytest-asyncio**: 异步测试
- **httpx**: HTTP 客户端测试
- **testcontainers**: Docker 容器测试
- **pytest-postgresql**: PostgreSQL 测试

#### 覆盖范围
- API 端点测试
- 数据库操作测试
- Artifact 操作测试
- Worker 通信测试
- 调度器集成测试

#### 示例

```python
# tests/integration/test_api_endpoints.py

import pytest
from httpx import AsyncClient
from src.main import app
from src.db.database import get_database
from src.db.models import Project, Job
import uuid

@pytest.fixture
async def client():
    """创建测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def test_db():
    """创建测试数据库"""
    # 使用 testcontainers 创建临时 PostgreSQL
    from testcontainers.postgres import PostgresContainer

    postgres = PostgresContainer("postgres:15-alpine")
    postgres.start()

    # 运行迁移
    import subprocess
    subprocess.run([
        "alembic", "upgrade", "head",
        "-x", f"sqlalchemy.url={postgres.get_connection_url()}"
    ])

    yield postgres.get_connection_url()

    postgres.stop()

@pytest.mark.asyncio
async def test_create_project(client, test_db):
    """测试创建项目"""
    # 覆盖数据库依赖
    async def override_get_database():
        return test_db

    app.dependency_overrides[get_database] = override_get_database

    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "Test Project",
            "media_type": "tv_series",
            "title": "测试剧集",
            "season": 1
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Test Project"
    assert "id" in data["data"]

@pytest.mark.asyncio
async def test_get_project(client, test_db):
    """测试获取项目"""
    # 先创建项目
    create_response = await client.post(
        "/api/v1/projects",
        json={"name": "Test Project"}
    )
    project_id = create_response.json()["data"]["id"]

    # 获取项目
    response = await client.get(f"/api/v1/projects/{project_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["id"] == project_id

@pytest.mark.asyncio
async def test_create_job(client, test_db):
    """测试创建 Job"""
    # 先创建项目
    project_response = await client.post(
        "/api/v1/projects",
        json={"name": "Test Project"}
    )
    project_id = project_response.json()["data"]["id"]

    # 创建 Job
    response = await client.post(
        f"/api/v1/projects/{project_id}/jobs",
        json={
            "name": "E01",
            "module_id": "M01",
            "config": {}
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["module_id"] == "M01"

@pytest.mark.asyncio
async def test_worker_registration(client):
    """测试 Worker 注册"""
    response = await client.post(
        "/api/v1/workers/register",
        json={
            "name": "test-worker",
            "type": "gpu",
            "resources": {
                "cpu_cores": 8,
                "memory_gb": 32,
                "gpu_count": 1
            },
            "capabilities": {
                "modules": ["M09"]
            }
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "worker_id" in data["data"]
    assert "worker_token" in data["data"]
```

### 3. 端到端测试

#### 目标
- 测试完整的工作流
- 验证系统整体功能
- 模拟真实用户场景

#### 工具
- **pytest-playwright**: 浏览器自动化
- **pytest-docker**: Docker 环境测试
- **requests**: HTTP 客户端

#### 测试场景

```python
# tests/e2e/test_complete_workflow.py

import pytest
import requests
import time
import os

class TestCompleteWorkflow:
    """完整工作流测试"""

    @pytest.fixture
    def api_base(self):
        """API 基础 URL"""
        return os.getenv("API_BASE_URL", "http://localhost:8000")

    @pytest.fixture
    def auth_token(self, api_base):
        """获取认证 Token"""
        response = requests.post(
            f"{api_base}/api/v1/auth/login",
            json={
                "username": "test_user",
                "password": "test_password"
            }
        )
        return response.json()["data"]["access_token"]

    def test_single_episode_workflow(self, api_base, auth_token):
        """测试单集完整工作流"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        # 1. 创建项目
        project_response = requests.post(
            f"{api_base}/api/v1/projects",
            headers=headers,
            json={
                "name": "Breaking Bad S01E01",
                "media_type": "tv_series",
                "title": "绝命毒师",
                "season": 1,
                "episode": 1
            }
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["data"]["id"]

        # 2. 上传视频
        with open("tests/fixtures/sample_video.mp4", "rb") as f:
            video_response = requests.post(
                f"{api_base}/api/v1/projects/{project_id}/upload-video",
                headers=headers,
                files={"video": f}
            )
        assert video_response.status_code == 200

        # 3. 上传字幕
        with open("tests/fixtures/sample_subtitle.srt", "rb") as f:
            subtitle_response = requests.post(
                f"{api_base}/api/v1/projects/{project_id}/upload-subtitle",
                headers=headers,
                files={"subtitle": f}
            )
        assert subtitle_response.status_code == 200

        # 4. 启动工作流
        workflow_response = requests.post(
            f"{api_base}/api/v1/projects/{project_id}/start",
            headers=headers
        )
        assert workflow_response.status_code == 200
        job_id = workflow_response.json()["data"]["job_id"]

        # 5. 等待完成
        max_wait = 600  # 10 分钟
        wait_interval = 10

        for _ in range(max_wait // wait_interval):
            time.sleep(wait_interval)

            status_response = requests.get(
                f"{api_base}/api/v1/jobs/{job_id}",
                headers=headers
            )
            status = status_response.json()["data"]["status"]

            if status in ["completed", "failed"]:
                break

        assert status == "completed"

        # 6. 获取结果
        result_response = requests.get(
            f"{api_base}/api/v1/projects/{project_id}/result",
            headers=headers
        )
        assert result_response.status_code == 200

        result = result_response.json()["data"]
        assert "final_video" in result
        assert result["final_video"]["status"] == "ready"

    def test_batch_season_workflow(self, api_base, auth_token):
        """测试批量季集工作流"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        # 创建季项目
        project_response = requests.post(
            f"{api_base}/api/v1/projects",
            headers=headers,
            json={
                "name": "Breaking Bad Season 1",
                "media_type": "tv_series",
                "title": "绝命毒师",
                "season": 1
            }
        )
        project_id = project_response.json()["data"]["id"]

        # 批量上传
        episodes = []
        for episode in range(1, 8):  # 7 集
            # 上传视频和字幕
            # ...

            episodes.append({
                "episode": episode,
                "video_artifact_id": "...",
                "subtitle_artifact_id": "..."
            })

        # 启动批量处理
        batch_response = requests.post(
            f"{api_base}/api/v1/projects/{project_id}/start-batch",
            headers=headers,
            json={"episodes": episodes}
        )

        assert batch_response.status_code == 200

        # 验证批量任务创建
        jobs = batch_response.json()["data"]["jobs"]
        assert len(jobs) == 7
```

## 性能测试

### 负载测试

```python
# tests/performance/test_load.py

import pytest
import asyncio
from httpx import AsyncClient
import time
from locust import HttpUser, task, between

class LoadTestUser(HttpUser):
    """负载测试用户"""
    wait_time = between(1, 3)

    def on_start(self):
        """登录获取 Token"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "test_user",
            "password": "test_password"
        })
        self.token = response.json()["data"]["access_token"]

    @task(3)
    def get_projects(self):
        """获取项目列表"""
        self.client.get(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {self.token}"}
        )

    @task(2)
    def get_project_status(self):
        """获取项目状态"""
        self.client.get(
            f"/api/v1/projects/test-project-id",
            headers={"Authorization": f"Bearer {self.token}"}
        )

    @task(1)
    def create_project(self):
        """创建项目"""
        self.client.post(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "name": f"Load Test Project {time.time()}",
                "media_type": "tv_series"
            }
        )

# 运行: locust -f tests/performance/test_load.py
```

### 压力测试

```python
# tests/performance/test_stress.py

import pytest
import asyncio
from httpx import AsyncClient, TimeoutException
import statistics

@pytest.mark.asyncio
async def test_api_concurrent_requests():
    """测试 API 并发请求"""
    base_url = "http://localhost:8000"
    num_requests = 100
    concurrency = 10

    async def make_request(client, request_id):
        try:
            start = time.time()
            response = await client.get(f"{base_url}/api/v1/projects")
            elapsed = time.time() - start
            return {
                "request_id": request_id,
                "status_code": response.status_code,
                "elapsed": elapsed
            }
        except TimeoutException:
            return {
                "request_id": request_id,
                "status_code": None,
                "elapsed": None,
                "timeout": True
            }

    async with AsyncClient() as client:
        # 登录
        login_response = await client.post(
            f"{base_url}/api/v1/auth/login",
            json={"username": "test", "password": "test"}
        )
        token = login_response.json()["data"]["access_token"]

        # 设置认证
        client.headers.update({"Authorization": f"Bearer {token}"})

        # 并发请求
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_request(request_id):
            async with semaphore:
                return await make_request(client, request_id)

        tasks = [
            bounded_request(i)
            for i in range(num_requests)
        ]

        results = await asyncio.gather(*tasks)

        # 分析结果
        successful = [r for r in results if not r.get("timeout")]
        timeouts = [r for r in results if r.get("timeout")]

        response_times = [r["elapsed"] for r in successful]

        print(f"Total requests: {num_requests}")
        print(f"Successful: {len(successful)}")
        print(f"Timeouts: {len(timeouts)}")
        print(f"Avg response time: {statistics.mean(response_times):.2f}s")
        print(f"P50: {statistics.median(response_times):.2f}s")
        print(f"P95: {sorted(response_times)[int(len(response_times) * 0.95)]:.2f}s")

        # 断言
        assert len(successful) > num_requests * 0.95  # 95% 成功率
        assert statistics.median(response_times) < 1.0  # 中位数 < 1s
```

## 测试配置

### pytest.ini

```ini
[pytest]
# 测试目录
testpaths = tests

# 文件匹配模式
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

# 标记
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests
    gpu: Tests requiring GPU
    external: Tests requiring external services

# 覆盖率配置
addopts =
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=70

# 异步模式
asyncio_mode = auto

# 日志
log_cli = true
log_cli_level = INFO

# 超时
timeout = 300
```

### conftest.py

```python
# tests/conftest.py

import pytest
import os
import asyncio
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from testcontainers.minio import MinioContainer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def postgres_container():
    """PostgreSQL 容器"""
    postgres = PostgresContainer("postgres:15-alpine")
    postgres.start()

    # 运行迁移
    os.environ["DATABASE_URL"] = postgres.get_connection_url()
    # 运行 alembic upgrade head

    yield postgres.get_connection_url()

    postgres.stop()

@pytest.fixture(scope="session")
async def redis_container():
    """Redis 容器"""
    redis = RedisContainer()
    redis.start()

    yield redis.get_connection_url()

    redis.stop()

@pytest.fixture(scope="session")
async def minio_container():
    """MinIO 容器"""
    minio = MinioContainer("minio/minio:latest")
    minio.start()

    yield {
        "endpoint": minio.get_endpoint(),
        "access_key": "minioadmin",
        "secret_key": "minioadmin123"
    }

    minio.stop()

@pytest.fixture
async def db_session(postgres_container):
    """数据库会话"""
    engine = create_async_engine(
        postgres_container.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()

@pytest.fixture
async def test_app(postgres_container, redis_container, minio_container):
    """测试应用实例"""
    from src.main import app
    from src.db.database import get_database
    from src.cache.redis import get_redis
    from src.storage.minio import get_minio

    # 覆盖依赖
    async def override_get_database():
        return postgres_container

    async def override_get_redis():
        return redis_container

    def override_get_minio():
        return minio_container

    app.dependency_overrides[get_database] = override_get_database
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[get_minio] = override_get_minio

    yield app

    app.dependency_overrides.clear()
```

## CI/CD 集成

### GitHub Actions 配置

```yaml
# .github/workflows/test.yml

name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run unit tests
        run: |
          pytest tests/unit -v --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_DB: testdb
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run integration tests
        run: |
          pytest tests/integration -v
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379/0

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Start services
        run: |
          docker-compose up -d

      - name: Run E2E tests
        run: |
          pytest tests/e2e -v --timeout=600
        env:
          API_BASE_URL: http://localhost:8000

      - name: Stop services
        if: always()
        run: |
          docker-compose down
```

## 测试数据管理

### Fixtures

```python
# tests/fixtures/data.py

import uuid
from src.db.models import Project, Job, Character, VoiceProfile
from datetime import datetime

def create_test_project(**kwargs):
    """创建测试项目"""
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test Project",
        "description": "Test Description",
        "status": "pending",
        "media_type": "tv_series",
        "title": "Test Show",
        "season": 1,
        "episode": 1,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    defaults.update(kwargs)
    return Project(**defaults)

def create_test_job(**kwargs):
    """创建测试 Job"""
    defaults = {
        "id": uuid.uuid4(),
        "project_id": uuid.uuid4(),
        "name": "Test Job",
        "status": "pending",
        "module_id": "M01",
        "retry_count": 0,
        "max_retries": 3,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    defaults.update(kwargs)
    return Job(**defaults)

def create_test_character(**kwargs):
    """创建测试人物"""
    defaults = {
        "id": uuid.uuid4(),
        "project_id": uuid.uuid4(),
        "name": "Test Character",
        "name_en": "Test Character",
        "gender": "male",
        "age_range": "adult",
        "role_type": "main",
        "is_active": True,
        "confidence": 1.0,
        "is_confirmed": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    defaults.update(kwargs)
    return Character(**defaults)

# 示例使用
@pytest.fixture
def sample_project():
    return create_test_project(
        name="Breaking Bad",
        title_en="Breaking Bad"
    )

@pytest.fixture
def sample_job(sample_project):
    return create_test_job(
        project_id=sample_project.id,
        module_id="M09"
    )
```

## Mock 和 Stub

### 外部服务 Mock

```python
# tests/mocks/external_services.py

from unittest.mock import Mock, AsyncMock, patch
import pytest

class MockTMDBClient:
    """TMDB 客户端 Mock"""

    async def search_tv(self, title: str, year: int = None):
        """搜索电视剧"""
        if "breaking bad" in title.lower():
            return {
                "results": [
                    {
                        "id": 1396,
                        "name": "Breaking Bad",
                        "first_air_date": "2008-01-20",
                        "vote_average": 9.5,
                        "overview": "A high school chemistry teacher..."
                    }
                ]
            }
        return {"results": []}

    async def get_tv_details(self, tmdb_id: int):
        """获取电视剧详情"""
        return {
            "id": tmdb_id,
            "name": "Breaking Bad",
            "seasons": [
                {"season_number": 1, "episode_count": 7}
            ],
            "credits": {
                "cast": [
                    {"id": 1747, "name": "Bryan Cranston", "character": "Walter White"}
                ]
            }
        }

@pytest.fixture
def mock_tmdb_client():
    """Mock TMDB 客户端"""
    with patch("src.external_services.tmdb.TMDBClient") as mock:
        client = MockTMDBClient()
        mock.return_value = client
        yield client

# 使用示例
@pytest.mark.asyncio
async def test_metadata_fetching(mock_tmdb_client):
    """测试元数据获取"""
    from src.modules.m01 import MetadataFetcher

    fetcher = MetadataFetcher("fake_api_key")

    metadata = await fetcher.fetch_metadata(
        M01Input(
            project_name="Breaking Bad",
            title_en="Breaking Bad",
            media_type=MediaType.TV_SERIES
        )
    )

    assert metadata.title_en == "Breaking Bad"
    assert len(metadata.seasons) == 1
```

## 最佳实践

1. **测试独立性**: 每个测试应该独立运行
2. **清理资源**: 使用 fixture 自动清理
3. **使用断言**: 明确的期望值
4. **测试命名**: 描述性的测试名称
5. **覆盖率监控**: CI 中检查覆盖率
6. **快速反馈**: 单元测试应该快速
7. **真实数据**: 使用真实的数据格式

## 后续决策

- 是否需要模糊测试
- 是否需要混沌工程测试
- 测试数据保留策略
