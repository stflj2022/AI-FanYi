"""
配置管理模块
"""
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 应用
    app_name: str = "AI-FanYi Orchestrator"
    app_version: str = "1.0.0"
    debug: bool = False

    # 数据库
    database_url: str = "postgresql+asyncpg://filmdub:filmdub@localhost:5432/filmdub"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "filmdub-artifacts"
    minio_secure: bool = False

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
    cors_origins: list = ["http://localhost:5173", "http://localhost:3000"]

    # API
    api_v1_prefix: str = "/api/v1"

    class Config:
        env_file = ".env"
        case_sensitive = False
        # extra = "forbid"  # 暂时禁用以支持更多配置


# 全局配置实例
settings = Settings()
