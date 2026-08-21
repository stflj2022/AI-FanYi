"""
JWT Token 处理

使用标准库实现的 HS256 JWT（RFC 7519），用于 Worker 认证。
不依赖第三方库（python-jose / pyjwt），保证在最小依赖环境下可用。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class JWTError(Exception):
    """JWT 编解码错误。"""


def _b64url_encode(data: bytes) -> str:
    """Base64url 编码（无填充）。"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    """Base64url 解码（自动补全填充）。"""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _now() -> int:
    """当前 UTC 时间戳（秒）。"""
    return int(datetime.now(timezone.utc).timestamp())


class JWTHandler:
    """JWT 处理器（HS256，纯标准库实现）。"""

    def __init__(
        self,
        secret_key: str = None,
        algorithm: str = "HS256",
        expiration_hours: int = 24,
    ):
        self.secret_key = secret_key or "your-secret-key-change-in-production"
        self.algorithm = algorithm
        self.expiration_hours = expiration_hours

    def _sign(self, signing_input: bytes) -> bytes:
        """使用 HMAC-SHA256 对输入进行签名。"""
        return hmac.new(
            self.secret_key.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()

    def encode(self, payload: Dict[str, Any]) -> str:
        """将载荷编码为 JWT。"""
        header = {"alg": self.algorithm, "typ": "JWT"}

        header_segment = _b64url_encode(
            json.dumps(header, separators=(",", ":")).encode("utf-8")
        )
        payload_segment = _b64url_encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )

        signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
        signature = _b64url_encode(self._sign(signing_input))

        return f"{header_segment}.{payload_segment}.{signature}"

    def decode(self, token: str, verify_exp: bool = True) -> Dict[str, Any]:
        """解码并验证 JWT。验证失败抛出 JWTError。"""
        if not isinstance(token, str):
            raise JWTError("Token must be a string")

        parts = token.split(".")
        if len(parts) != 3:
            raise JWTError("Invalid token structure")

        header_segment, payload_segment, signature_segment = parts

        try:
            header = json.loads(_b64url_decode(header_segment))
            payload = json.loads(_b64url_decode(payload_segment))
            signature = _b64url_decode(signature_segment)
        except (ValueError, json.JSONDecodeError) as e:
            raise JWTError(f"Malformed token: {e}")

        if header.get("alg") != self.algorithm:
            raise JWTError(f"Unsupported algorithm: {header.get('alg')}")

        # 验证签名
        signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
        expected = self._sign(signing_input)
        if not hmac.compare_digest(signature, expected):
            raise JWTError("Invalid signature")

        # 验证过期时间
        if verify_exp and "exp" in payload:
            if _now() >= int(payload["exp"]):
                raise JWTError("Token expired")

        return payload

    def create_token(
        self,
        worker_id: str,
        payload: Dict[str, Any] = None,
    ) -> str:
        """创建 Worker Token。"""
        payload = dict(payload or {})
        payload.update(
            {
                "worker_id": worker_id,
                "type": "worker",
                "iat": _now(),
                "exp": _now() + self.expiration_hours * 3600,
            }
        )

        token = self.encode(payload)
        logger.debug(f"Created token for worker {worker_id}")
        return token

    # 别名，保持与调度器/其他调用方的兼容
    generate_token = create_token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证 Token，返回载荷或 None。"""
        try:
            payload = self.decode(token)

            if payload.get("type") != "worker":
                logger.warning(f"Invalid token type: {payload.get('type')}")
                return None

            return payload
        except JWTError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def decode_token(self, token: str) -> Optional[str]:
        """解码 Token（不验证过期时间），返回 Worker ID 或 None。"""
        try:
            payload = self.decode(token, verify_exp=False)

            if payload.get("type") != "worker":
                return None

            return payload.get("worker_id")
        except JWTError as e:
            logger.warning(f"Failed to decode token: {e}")
            return None
