"""
Layer 0 Orchestrator 配置管理模块
"""
from typing import Optional
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class OrchestratorSettings(BaseSettings):
    """Layer 0 Orchestrator 配置"""

    # 应用
    app_name: str = "AI-FanYi Orchestrator"
    app_version: str = "1.0.0"
    debug: bool = False

    # 数据库 (开发环境使用 SQLite，生产环境使用 PostgreSQL)
    database_url: str = "sqlite+aiosqlite:///./filmdub_orchestrator.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "filmdub-artifacts"
    minio_secure: bool = False

    # Artifact 存储后端: local | minio | auto（auto=仅当显式设置 MINIO_ENDPOINT 时使用 MinIO）
    artifact_storage_backend: str = "auto"

    # JWT
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Worker
    worker_heartbeat_interval: int = 10
    worker_heartbeat_timeout: int = 60

    # 调度器
    scheduler_cycle_interval: int = 1  # 秒
    scheduler_max_retries: int = 3

    # 监控
    metrics_port: int = 9090
    jaeger_endpoint: Optional[str] = None

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # API
    api_v1_prefix: str = "/api/v1"

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )


# 全局配置实例
orchestrator_settings = OrchestratorSettings()
