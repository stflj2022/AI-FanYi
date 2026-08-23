"""错误处理服务"""
from typing import Optional, Dict, Any
from datetime import datetime
import traceback

from filmdub.apps.web.backend.config.error_codes import (
    ErrorCode,
    ErrorType,
    get_error_message,
    get_error_by_code,
)


class ErrorMapping:
    """错误映射对象"""

    def __init__(
        self,
        error_code: ErrorCode,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.error_code = error_code
        self.original_error = original_error
        self.context = context or {}

        # 获取用户友好的消息
        self.message_config = get_error_message(error_code)
        self.title = self.message_config["title"]
        self.message = self.message_config["message"]
        self.suggestion = self.message_config["suggestion"]
        self.error_type = self.message_config["type"]
        self.timestamp = datetime.utcnow()

        # 错误详情（用于日志）
        self.details = self._build_details()

    def _build_details(self) -> Dict[str, Any]:
        """构建错误详情"""
        details = {
            "error_code": self.error_code.value,
            "error_type": self.error_type.value,
            "title": self.title,
            "message": self.message,
            "suggestion": self.suggestion,
            "timestamp": self.timestamp.isoformat(),
        }

        # 添加原始错误信息
        if self.original_error:
            details["original_error"] = str(self.original_error)
            details["error_type_name"] = type(self.original_error).__name__

            # 添加堆栈跟踪
            details["stack_trace"] = traceback.format_exc()

        # 添加上下文信息
        if self.context:
            details["context"] = self.context

        return details

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.details

    def to_user_dict(self) -> Dict[str, str]:
        """转换为用户友好的字典（不包含技术细节）"""
        return {
            "error_code": self.error_code.value,
            "title": self.title,
            "message": self.message,
            "suggestion": self.suggestion,
            "type": self.error_type.value,
        }


class ErrorService:
    """错误处理服务"""

    @staticmethod
    def map_error(
        error: Exception,
        default_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        context: Optional[Dict[str, Any]] = None,
    ) -> ErrorMapping:
        """
        将异常映射为用户友好的错误消息

        Args:
            error: 原始异常
            default_code: 默认错误码
            context: 额外的上下文信息

        Returns:
            ErrorMapping 对象
        """
        # 根据异常类型确定错误码
        error_code = ErrorService._determine_error_code(error, default_code)

        return ErrorMapping(
            error_code=error_code,
            original_error=error,
            context=context,
        )

    @staticmethod
    def map_error_code(
        code: str,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ErrorMapping:
        """
        根据错误码创建错误映射

        Args:
            code: 错误码字符串
            original_error: 原始异常（可选）
            context: 额外的上下文信息

        Returns:
            ErrorMapping 对象
        """
        error_code = get_error_by_code(code) or ErrorCode.UNKNOWN_ERROR

        return ErrorMapping(
            error_code=error_code,
            original_error=original_error,
            context=context,
        )

    @staticmethod
    def _determine_error_code(
        error: Exception,
        default_code: ErrorCode
    ) -> ErrorCode:
        """
        根据异常类型确定错误码

        Args:
            error: 异常对象
            default_code: 默认错误码

        Returns:
            错误码
        """
        error_type = type(error).__name__
        error_message = str(error).lower()

        # 根据异常类型和消息匹配错误码
        if "timeout" in error_type.lower() or "timeout" in error_message:
            return ErrorCode.JOB_TIMEOUT
        elif "notfound" in error_type.lower() or "not found" in error_message:
            return ErrorCode.NOT_FOUND
        elif "permission" in error_type.lower() or "permission" in error_message:
            return ErrorCode.PERMISSION_DENIED
        elif "validation" in error_type.lower() or "validation" in error_message:
            return ErrorCode.VALIDATION_ERROR
        elif "connection" in error_type.lower():
            if "timeout" in error_message:
                return ErrorCode.CONNECTION_TIMEOUT
            elif "refused" in error_message:
                return ErrorCode.CONNECTION_REFUSED
            return ErrorCode.NETWORK_ERROR
        elif "file" in error_type.lower():
            if "too large" in error_message or "size" in error_message:
                return ErrorCode.UPLOAD_FILE_TOO_LARGE
            elif "format" in error_message or "invalid" in error_message:
                return ErrorCode.UPLOAD_INVALID_FORMAT
            return ErrorCode.RESOURCE_NOT_FOUND
        elif "storage" in error_type.lower() or "disk" in error_message:
            if "full" in error_message or "space" in error_message:
                return ErrorCode.STORAGE_FULL
            return ErrorCode.RESOURCE_CORRUPTED

        return default_code

    @staticmethod
    def create_user_error_response(
        error_mapping: ErrorMapping,
    ) -> Dict[str, Any]:
        """
        创建用户错误响应（用于 API 返回）

        Args:
            error_mapping: 错误映射对象

        Returns:
            用户友好的错误响应
        """
        return {
            "success": False,
            "error": error_mapping.to_user_dict(),
        }

    @staticmethod
    def log_error(error_mapping: ErrorMapping, level: str = "ERROR"):
        """
        记录错误日志

        Args:
            error_mapping: 错误映射对象
            level: 日志级别
        """
        import logging

        logger = logging.getLogger(__name__)

        log_message = f"[{error_mapping.error_code.value}] {error_mapping.title}: {error_mapping.message}"

        if level == "ERROR":
            logger.error(log_message, exc_info=error_mapping.original_error)
        elif level == "WARNING":
            logger.warning(log_message)
        elif level == "INFO":
            logger.info(log_message)
        else:
            logger.debug(log_message)
