"""错误码和用户友好消息映射"""
from enum import Enum
from typing import Dict, Optional


class ErrorType(str, Enum):
    """错误类型"""
    RECOVERABLE = "recoverable"  # 可恢复
    RETRYABLE = "retryable"  # 可重试
    MANUAL = "manual"  # 需人工干预
    FATAL = "fatal"  # 致命错误


class ErrorCode(str, Enum):
    """错误码定义"""
    # 通用错误 (1000-1999)
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # 上传相关错误 (2000-2999)
    UPLOAD_FILE_TOO_LARGE = "UPLOAD_FILE_TOO_LARGE"
    UPLOAD_INVALID_FORMAT = "UPLOAD_INVALID_FORMAT"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    UPLOAD_INCOMPLETE = "UPLOAD_INCOMPLETE"

    # 任务相关错误 (3000-3999)
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_ALREADY_RUNNING = "JOB_ALREADY_RUNNING"
    JOB_DEPENDENCY_FAILED = "JOB_DEPENDENCY_FAILED"
    JOB_TIMEOUT = "JOB_TIMEOUT"
    JOB_CANCELLED = "JOB_CANCELLED"
    WORKER_UNAVAILABLE = "WORKER_UNAVAILABLE"

    # 模块相关错误 (4000-4999)
    MODULE_NOT_FOUND = "MODULE_NOT_FOUND"
    MODULE_FAILED = "MODULE_FAILED"
    MODULE_TIMEOUT = "MODULE_TIMEOUT"

    # 资源相关错误 (5000-5999)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_CORRUPTED = "RESOURCE_CORRUPTED"
    STORAGE_FULL = "STORAGE_FULL"

    # 外部服务错误 (6000-6999)
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    EXTERNAL_SERVICE_TIMEOUT = "EXTERNAL_SERVICE_TIMEOUT"
    AI_MODEL_ERROR = "AI_MODEL_ERROR"

    # 网络错误 (7000-7999)
    NETWORK_ERROR = "NETWORK_ERROR"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    CONNECTION_REFUSED = "CONNECTION_REFUSED"


# 错误消息映射
ERROR_MESSAGES: Dict[ErrorCode, Dict[str, str]] = {
    # 通用错误
    ErrorCode.UNKNOWN_ERROR: {
        "title": "未知错误",
        "message": "发生了未知错误，请稍后重试",
        "suggestion": "如果问题持续存在，请联系技术支持",
        "type": ErrorType.RETRYABLE,
    },
    ErrorCode.VALIDATION_ERROR: {
        "title": "数据验证失败",
        "message": "输入的数据不符合要求",
        "suggestion": "请检查输入内容并重试",
        "type": ErrorType.RECOVERABLE,
    },
    ErrorCode.NOT_FOUND: {
        "title": "资源不存在",
        "message": "请求的资源不存在或已被删除",
        "suggestion": "请确认资源 ID 是否正确",
        "type": ErrorType.FATAL,
    },
    ErrorCode.PERMISSION_DENIED: {
        "title": "权限不足",
        "message": "您没有权限执行此操作",
        "suggestion": "请联系管理员获取相应权限",
        "type": ErrorType.FATAL,
    },
    ErrorCode.RATE_LIMIT_EXCEEDED: {
        "title": "请求过于频繁",
        "message": "您的请求过于频繁，请稍后再试",
        "suggestion": "请等待几秒后再试",
        "type": ErrorType.RECOVERABLE,
    },

    # 上传相关错误
    ErrorCode.UPLOAD_FILE_TOO_LARGE: {
        "title": "文件过大",
        "message": "上传的文件超过了最大限制",
        "suggestion": "请压缩文件或选择更小的文件",
        "type": ErrorType.RECOVERABLE,
    },
    ErrorCode.UPLOAD_INVALID_FORMAT: {
        "title": "文件格式不支持",
        "message": "上传的文件格式不支持",
        "suggestion": "请上传支持的文件格式（MP4, MOV, AVI, MKV 等）",
        "type": ErrorType.RECOVERABLE,
    },
    ErrorCode.UPLOAD_FAILED: {
        "title": "上传失败",
        "message": "文件上传过程中发生错误",
        "suggestion": "请检查网络连接后重试",
        "type": ErrorType.RETRYABLE,
    },
    ErrorCode.UPLOAD_INCOMPLETE: {
        "title": "上传未完成",
        "message": "文件上传未完成",
        "suggestion": "请重新上传文件",
        "type": ErrorType.RETRYABLE,
    },

    # 任务相关错误
    ErrorCode.JOB_NOT_FOUND: {
        "title": "任务不存在",
        "message": "指定的任务不存在或已被删除",
        "suggestion": "请检查任务 ID 是否正确",
        "type": ErrorType.FATAL,
    },
    ErrorCode.JOB_ALREADY_RUNNING: {
        "title": "任务正在运行",
        "message": "该任务已经在运行中",
        "suggestion": "请等待任务完成或先取消当前任务",
        "type": ErrorType.FATAL,
    },
    ErrorCode.JOB_DEPENDENCY_FAILED: {
        "title": "依赖任务失败",
        "message": "任务依赖的前置任务执行失败",
        "suggestion": "请检查并修复依赖任务后重试",
        "type": ErrorType.MANUAL,
    },
    ErrorCode.JOB_TIMEOUT: {
        "title": "任务超时",
        "message": "任务执行时间超过限制",
        "suggestion": "可以尝试重新运行任务，或者检查是否有性能问题",
        "type": ErrorType.RETRYABLE,
    },
    ErrorCode.JOB_CANCELLED: {
        "title": "任务已取消",
        "message": "任务已被取消",
        "suggestion": "如需继续，请重新创建任务",
        "type": ErrorType.FATAL,
    },
    ErrorCode.WORKER_UNAVAILABLE: {
        "title": "工作节点不可用",
        "message": "执行任务的工作节点不可用",
        "suggestion": "请稍后重试，或联系管理员检查工作节点状态",
        "type": ErrorType.RETRYABLE,
    },

    # 模块相关错误
    ErrorCode.MODULE_NOT_FOUND: {
        "title": "模块不存在",
        "message": "指定的处理模块不存在",
        "suggestion": "请联系技术支持",
        "type": ErrorType.FATAL,
    },
    ErrorCode.MODULE_FAILED: {
        "title": "模块执行失败",
        "message": "处理模块执行过程中发生错误",
        "suggestion": "请查看错误日志获取详细信息",
        "type": ErrorType.MANUAL,
    },
    ErrorCode.MODULE_TIMEOUT: {
        "title": "模块执行超时",
        "message": "处理模块执行时间超过限制",
        "suggestion": "可以尝试重新运行任务",
        "type": ErrorType.RETRYABLE,
    },

    # 资源相关错误
    ErrorCode.RESOURCE_NOT_FOUND: {
        "title": "资源不存在",
        "message": "指定的资源文件不存在",
        "suggestion": "请确认资源路径是否正确",
        "type": ErrorType.FATAL,
    },
    ErrorCode.RESOURCE_CORRUPTED: {
        "title": "资源文件损坏",
        "message": "资源文件已损坏，无法使用",
        "suggestion": "请重新上传或修复资源文件",
        "type": ErrorType.MANUAL,
    },
    ErrorCode.STORAGE_FULL: {
        "title": "存储空间不足",
        "message": "系统存储空间不足",
        "suggestion": "请联系管理员扩容或清理空间",
        "type": ErrorType.FATAL,
    },

    # 外部服务错误
    ErrorCode.EXTERNAL_SERVICE_ERROR: {
        "title": "外部服务错误",
        "message": "调用的外部服务返回错误",
        "suggestion": "请稍后重试，或联系技术支持",
        "type": ErrorType.RETRYABLE,
    },
    ErrorCode.EXTERNAL_SERVICE_TIMEOUT: {
        "title": "外部服务超时",
        "message": "外部服务响应超时",
        "suggestion": "请稍后重试",
        "type": ErrorType.RETRYABLE,
    },
    ErrorCode.AI_MODEL_ERROR: {
        "title": "AI 模型错误",
        "message": "AI 模型执行过程中发生错误",
        "suggestion": "可以尝试重新运行任务",
        "type": ErrorType.RETRYABLE,
    },

    # 网络错误
    ErrorCode.NETWORK_ERROR: {
        "title": "网络错误",
        "message": "网络连接发生错误",
        "suggestion": "请检查网络连接后重试",
        "type": ErrorType.RETRYABLE,
    },
    ErrorCode.CONNECTION_TIMEOUT: {
        "title": "连接超时",
        "message": "服务器连接超时",
        "suggestion": "请检查网络连接或稍后重试",
        "type": ErrorType.RETRYABLE,
    },
    ErrorCode.CONNECTION_REFUSED: {
        "title": "连接被拒绝",
        "message": "服务器拒绝连接",
        "suggestion": "请联系技术支持检查服务器状态",
        "type": ErrorType.FATAL,
    },
}


def get_error_message(
    error_code: ErrorCode,
    lang: str = "zh"
) -> Dict[str, str]:
    """
    获取错误消息

    Args:
        error_code: 错误码
        lang: 语言代码（默认中文）

    Returns:
        包含 title, message, suggestion, type 的字典
    """
    if error_code not in ERROR_MESSAGES:
        error_code = ErrorCode.UNKNOWN_ERROR

    return ERROR_MESSAGES[error_code]


def get_error_by_code(code_str: str) -> Optional[ErrorCode]:
    """
    通过字符串获取错误码枚举

    Args:
        code_str: 错误码字符串

    Returns:
        ErrorCode 枚举，如果不存在则返回 None
    """
    try:
        return ErrorCode(code_str)
    except ValueError:
        return None
