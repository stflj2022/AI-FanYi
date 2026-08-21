"""File hashing utilities."""

import hashlib
from pathlib import Path


def compute_sha256(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    """Compute SHA-256 hash of a file.

    Args:
        path: Path to file.
        chunk_size: Chunk size for reading (default: 8MB).

    Returns:
        str: Hexadecimal SHA-256 hash.
    """
    digest = hashlib.sha256()

    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)

    return digest.hexdigest()


def verify_sha256(path: Path, expected_hash: str, chunk_size: int = 8 * 1024 * 1024) -> bool:
    """Verify file SHA-256 hash.

    Args:
        path: Path to file.
        expected_hash: Expected SHA-256 hash.
        chunk_size: Chunk size for reading.

    Returns:
        bool: True if hash matches.
    """
    actual = compute_sha256(path, chunk_size)
    return actual.lower() == expected_hash.lower()
