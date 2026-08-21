"""Storage management for projects and media."""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Optional

from filmdub.core.config import settings


class StorageManager:
    """Manages file storage for projects."""

    def __init__(self, project_id: Optional[str] = None):
        """Initialize storage manager.

        Args:
            project_id: Optional project ID.
        """
        self.project_id = project_id

    @property
    def projects_base(self) -> Path:
        """Get base projects directory."""
        return settings.projects_base_dir

    @property
    def upload_temp(self) -> Path:
        """Get upload temp directory."""
        return settings.upload_temp_dir

    def ensure_directories(self) -> None:
        """Ensure all necessary directories exist."""
        if not self.project_id:
            raise ValueError("project_id is required")

        dirs = [
            self.get_project_dir(),
            self.get_media_dir(),
            self.get_manifests_dir(),
            self.get_logs_dir(),
            self.get_jobs_dir(),
        ]

        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)

    def get_project_dir(self) -> Path:
        """Get project directory."""
        if not self.project_id:
            raise ValueError("project_id is required")
        return settings.get_project_dir(self.project_id)

    def get_media_dir(self, media_id: Optional[str] = None) -> Path:
        """Get media directory.

        Args:
            media_id: Optional media ID. If provided, returns media-specific directory.
        """
        if not self.project_id:
            raise ValueError("project_id is required")
        if media_id:
            return settings.get_media_dir(self.project_id, media_id)
        return settings.get_project_dir(self.project_id) / "media"

    def get_manifests_dir(self) -> Path:
        """Get manifests directory."""
        if not self.project_id:
            raise ValueError("project_id is required")
        return settings.get_manifests_dir(self.project_id)

    def get_logs_dir(self) -> Path:
        """Get logs directory."""
        if not self.project_id:
            raise ValueError("project_id is required")
        return settings.get_logs_dir(self.project_id)

    def get_jobs_dir(self) -> Path:
        """Get jobs directory."""
        if not self.project_id:
            raise ValueError("project_id is required")
        return settings.get_jobs_dir(self.project_id)

    def get_original_media_path(self, media_id: str) -> Path:
        """Get path for original media file.

        Args:
            media_id: Media ID.

        Returns:
            Path: Path to original media file.
        """
        if not self.project_id:
            raise ValueError("project_id is required")
        media_dir = self.get_media_dir(media_id)
        return media_dir / "original.mkv"

    def save_uploaded_file(self, temp_path: Path, media_id: str, original_filename: str) -> Path:
        """Save uploaded file to permanent storage.

        Args:
            temp_path: Temporary file path.
            media_id: Media ID.
            original_filename: Original filename.

        Returns:
            Path: Path to saved file.
        """
        self.ensure_directories()

        # Save as original.mkv (immutable name)
        target_path = self.get_original_media_path(media_id)

        # Ensure media directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: copy to temp then rename
        temp_target = target_path.with_suffix(".tmp")
        shutil.copy2(temp_path, temp_target)
        temp_target.rename(target_path)

        return target_path

    def save_manifest(self, name: str, data: dict) -> Path:
        """Save manifest to file.

        Args:
            name: Manifest name (without extension).
            data: Manifest data.

        Returns:
            Path: Path to saved manifest.
        """
        self.ensure_directories()
        manifest_path = self.get_manifests_dir() / f"{name}.json"

        # Atomic write
        temp_path = manifest_path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path.replace(manifest_path)

        return manifest_path

    def load_manifest(self, name: str) -> Optional[dict]:
        """Load manifest from file.

        Args:
            name: Manifest name (without extension).

        Returns:
            Optional[dict]: Manifest data, or None if not found.
        """
        manifest_path = self.get_manifests_dir() / f"{name}.json"
        if not manifest_path.exists():
            return None

        with manifest_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def append_log(self, log_name: str, entry: dict) -> None:
        """Append entry to log file (JSONL).

        Args:
            log_name: Log name (without extension).
            entry: Log entry.
        """
        self.ensure_directories()
        log_path = self.get_logs_dir() / f"{log_name}.jsonl"

        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_temp_upload_path(self, filename: str) -> Path:
        """Get temporary upload path.

        Args:
            filename: Original filename.

        Returns:
            Path: Temporary file path.
        """
        self.upload_temp.mkdir(parents=True, exist_ok=True)
        return self.upload_temp / filename

    @staticmethod
    def compute_sha256(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
        """Compute SHA-256 hash of a file.

        Args:
            path: File path.
            chunk_size: Chunk size for reading.

        Returns:
            str: Hexadecimal SHA-256 hash.
        """
        digest = hashlib.sha256()
        with path.open("rb") as f:
            while chunk := f.read(chunk_size):
                digest.update(chunk)
        return digest.hexdigest()

    def cleanup_temp_file(self, path: Path) -> None:
        """Safely remove temporary file.

        Args:
            path: File path to remove.
        """
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass  # Ignore cleanup errors

    def get_file_size(self, path: Path) -> int:
        """Get file size in bytes.

        Args:
            path: File path.

        Returns:
            int: File size in bytes.
        """
        return path.stat().st_size
