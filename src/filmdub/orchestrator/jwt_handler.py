"""
JWT Token 处理

简化版 JWT 实现，用于 Worker 认证
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from loguru import logger

from jose import jwt
from jose.exceptions import JWTError


class JWTHandler:
    """JWT 处理器"""

    def __init__(
        self,
        secret_key: str = None,
        algorithm: str = "HS256",
        expiration_hours: int = 24
    ):
        """
        初始化 JWT 处理器

        Args:
            secret_key: 密钥
            algorithm: 算法
            expiration_hours: 过期时间（小时）
        """
        self.secret_key = secret_key or "your-secret-key-change-in-production"
        self.algorithm = algorithm
        self.expiration_hours = expiration_hours

    def create_token(
        self,
        worker_id: str,
        payload: Dict[str, Any] = None
    ) -> str:
        """
        创建 Worker Token

        Args:
            worker_id: Worker ID
            payload: 额外载荷

        Returns:
            JWT Token
        """
        now = datetime.utcnow()

        payload = payload or {}
        payload.update({
            "worker_id": worker_id,
            "type": "worker",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=self.expiration_hours)).timestamp())
        })

        token = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm
        )

        logger.debug(f"Created token for worker {worker_id}")

        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证 Token

        Args:
            token: JWT Token

        Returns:
            Payload 或 None
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            # 验证 Token 类型
            if payload.get("type") != "worker":
                logger.warning(f"Invalid token type: {payload.get('type')}")
                return None

            # 检查过期时间
            if "exp" in payload:
                exp = datetime.fromtimestamp(payload["exp"])
                if datetime.utcnow() >= exp:
                    logger.warning(f"Token expired for worker {payload.get('worker_id')}")
                    return None

            return payload

        except JWTError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def decode_token(self, token: str) -> Optional[str]:
        """
        解码 Token（不验证）

        Args:
            token: JWT Token

        Returns:
            Worker ID 或 None
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # 不验证过期时间
            )

            if payload.get("type") != "worker":
                return None

            return payload.get("worker_id")

        except JWTError as e:
            logger.warning(f"Failed to decode token: {e}")
            return None
