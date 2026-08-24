"""Core configuration for FilmDub AI."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    # Directories
    projects_base_dir: Path = Field(
        default=Path("./projects"),
        description="Base directory for project storage",
    )
    upload_temp_dir: Path = Field(
        default=Path("/tmp/filmdub_uploads"),
        description="Temporary directory for uploads",
    )
    upload_max_file_size_gb: float = Field(
        default=100.0,
        ge=0.1,
        le=1000.0,
        description="Maximum upload file size in GB",
    )

    # Database
    database_url_template: str = Field(
        default="sqlite+aiosqlite:///$PROJECTS_BASE_DIR/{project_id}/database.sqlite",
        description="Database URL template with {project_id} placeholder",
    )
    database_url: str = Field(
        default="postgresql+asyncpg://filmdub:filmdub@localhost:5432/filmdub",
        description="Main orchestrator database URL",
    )

    # API
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API port")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    debug: bool = Field(default=False, description="Debug mode")

    # Job System
    job_timeout_seconds: int = Field(
        default=3600,
        ge=60,
        description="Job timeout in seconds",
    )
    job_max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum job retry attempts",
    )

    # FFmpeg
    ffprobe_path: str = Field(default="ffprobe", description="Path to ffprobe executable")
    ffmpeg_path: str = Field(default="ffmpeg", description="Path to ffmpeg executable")

    # Web UI
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="CORS allowed origins",
    )
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT secret key for authentication",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=24, description="JWT token expiration in hours")

    # 本地免登录模式：true 时所有需认证接口自动使用本地用户（环境变量 AUTH_DISABLED=true）
    auth_disabled: bool = Field(
        default=False,
        description="Local no-login mode: skip authentication and use local user",
    )

    @field_validator("projects_base_dir", "upload_temp_dir", mode="before")
    @classmethod
    def resolve_path(cls, v: str | Path) -> Path:
        """Resolve string paths to Path objects."""
        if isinstance(v, str):
            # Expand environment variables and user home
            v = os.path.expandvars(os.path.expanduser(v))
        return Path(v).resolve()

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, v: str) -> str:
        """Normalize log level to uppercase."""
        return v.upper()

    def get_database_url(self, project_id: str) -> str:
        """Get database URL for a specific project."""
        return self.database_url_template.replace("$PROJECTS_BASE_DIR", str(self.projects_base_dir)).replace(
            "{project_id}", project_id
        )

    def get_project_dir(self, project_id: str) -> Path:
        """Get directory path for a project."""
        return self.projects_base_dir / project_id

    def get_media_dir(self, project_id: str, media_id: str) -> Path:
        """Get directory path for media assets."""
        return self.get_project_dir(project_id) / "media" / media_id

    def get_manifests_dir(self, project_id: str) -> Path:
        """Get directory path for manifests."""
        return self.get_project_dir(project_id) / "manifests"

    def get_logs_dir(self, project_id: str) -> Path:
        """Get directory path for logs."""
        return self.get_project_dir(project_id) / "logs"

    def get_jobs_dir(self, project_id: str) -> Path:
        """Get directory path for jobs."""
        return self.get_project_dir(project_id) / "jobs"


settings = Settings()
