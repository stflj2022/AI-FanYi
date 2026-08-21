# ADR 0007: 错误处理和重试策略

## 状态

设计中

## 上下文

分布式系统中，错误是常态。需要设计统一的错误处理和重试策略，确保系统可靠性和可维护性。

## 错误分类

### 1. 按来源分类

```python
from enum import Enum

class ErrorSource(Enum):
    """错误来源"""
    # Worker 层错误
    WORKER_EXECUTION = "worker_execution"      # Worker 执行失败
    WORKER_RESOURCE = "worker_resource"        # Worker 资源不足
    WORKER_TIMEOUT = "worker_timeout"          # Worker 超时
    WORKER_OFFLINE = "worker_offline"          # Worker 离线

    # Orchestrator 层错误
    SCHEDULER = "scheduler"                    # 调度器错误
    API = "api"                                # API 错误
    DATABASE = "database"                      # 数据库错误
    CACHE = "cache"                            # 缓存错误

    # Artifact 层错误
    ARTIFACT_UPLOAD = "artifact_upload"        # Artifact 上传失败
    ARTIFACT_DOWNLOAD = "artifact_download"    # Artifact 下载失败
    ARTIFACT_CORRUPTED = "artifact_corrupted"  # Artifact 损坏
    ARTIFACT_NOT_FOUND = "artifact_not_found"  # Artifact 不存在

    # 外部服务错误
    EXTERNAL_SERVICE = "external_service"     # 外部服务错误
    NETWORK = "network"                        # 网络错误

    # 用户错误
    USER_INPUT = "user_input"                  # 用户输入错误
    USER_CANCEL = "user_cancel"                # 用户取消
```

### 2. 按可恢复性分类

```python
class ErrorRecoverability(Enum):
    """错误可恢复性"""
    # 可恢复错误
    RETRYABLE_TEMPORARY = "retryable_temporary"    # 临时性错误，可重试
    RETRYABLE_RESOURCE = "retryable_resource"      # 资源不足，可重试
    RETRYABLE_DEPENDENCY = "retryable_dependency"  # 依赖不可用，可重试

    # 不可恢复错误
    NON_RETRYABLE_LOGIC = "non_retryable_logic"    # 逻辑错误，不可重试
    NON_RETRYABLE_DATA = "non_retryable_data"      # 数据错误，不可重试
    NON_RETRYABLE_CONFIG = "non_retryable_config"  # 配置错误，不可重试

    # 用户行为
    USER_CANCELLED = "user_cancelled"              # 用户取消
```

### 3. 按严重程度分类

```python
class ErrorSeverity(Enum):
    """错误严重程度"""
    INFO = "info"           # 信息性，不影响功能
    WARNING = "warning"     # 警告，可能影响功能但可继续
    ERROR = "error"         # 错误，功能受损但可恢复
    CRITICAL = "critical"   # 严重，系统无法正常工作
    FATAL = "fatal"         # 致命，需要立即人工介入
```

## 错误处理框架

### 统一错误类

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

@dataclass
class SystemError:
    """统一错误类"""
    error_id: uuid.UUID
    error_code: str                    # 唯一错误代码
    error_type: str                    # 错误类型
    message: str                       # 人类可读消息
    source: ErrorSource                # 错误来源
    recoverability: ErrorRecoverability  # 可恢复性
    severity: ErrorSeverity            # 严重程度

    # 上下文信息
    context: Dict[str, Any]           # 错误上下文
    stack_trace: Optional[str]         # 堆栈跟踪

    # 关联信息
    job_id: Optional[uuid.UUID]        # 关联的 Job ID
    worker_id: Optional[uuid.UUID]     # 关联的 Worker ID
    project_id: Optional[uuid.UUID]    # 关联的项目 ID
    artifact_id: Optional[uuid.UUID]   # 关联的 Artifact ID

    # 时间信息
    timestamp: datetime                 # 发生时间
    first_occurrence: datetime          # 首次发生时间
    occurrence_count: int = 1          # 发生次数

    # 处理信息
    is_handled: bool = False           # 是否已处理
    handler: Optional[str] = None      # 处理器
    resolution: Optional[str] = None   # 解决方案

    # 重试信息
    is_retryable: bool = False         # 是否可重试
    retry_count: int = 0               # 当前重试次数
    max_retries: Optional[int] = None  # 最大重试次数
    next_retry_at: Optional[datetime] = None  # 下次重试时间

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_id": str(self.error_id),
            "error_code": self.error_code,
            "error_type": self.error_type,
            "message": self.message,
            "source": self.source.value,
            "recoverability": self.recoverability.value,
            "severity": self.severity.value,
            "context": self.context,
            "stack_trace": self.stack_trace,
            "job_id": str(self.job_id) if self.job_id else None,
            "worker_id": str(self.worker_id) if self.worker_id else None,
            "project_id": str(self.project_id) if self.project_id else None,
            "artifact_id": str(self.artifact_id) if self.artifact_id else None,
            "timestamp": self.timestamp.isoformat(),
            "is_handled": self.is_handled,
            "is_retryable": self.is_retryable,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }
```

### 错误代码定义

```python
class ErrorCodes:
    """错误代码定义"""

    # Worker 执行错误 (WXXX)
    W001 = "WORKER_EXECUTION_FAILED"          # Worker 执行失败
    W002 = "WORKER_RESOURCE_INSUFFICIENT"     # Worker 资源不足
    W003 = "WORKER_TIMEOUT"                   # Worker 超时
    W004 = "WORKER_OFFLINE"                   # Worker 离线
    W005 = "WORKER_CRASHED"                   # Worker 崩溃
    W006 = "WORKER_STARTUP_FAILED"            # Worker 启动失败

    # 调度器错误 (SXXX)
    S001 = "SCHEDULER_NO_WORKER_AVAILABLE"    # 没有可用的 Worker
    S002 = "SCHEDULER_DISPATCH_FAILED"         # 分发失败
    S003 = "SCHEDULER_DEPENDENCY_ERROR"       # 依赖错误
    S004 = "SCHEDULER_CIRCULAR_DEPENDENCY"    # 循环依赖

    # Artifact 错误 (AXXX)
    A001 = "ARTIFACT_NOT_FOUND"                # Artifact 不存在
    A002 = "ARTIFACT_DOWNLOAD_FAILED"          # 下载失败
    A003 = "ARTIFACT_UPLOAD_FAILED"            # 上传失败
    A004 = "ARTIFACT_CHECKSUM_MISMATCH"        # 校验和不匹配
    A005 = "ARTIFACT_CORRUPTED"                # Artifact 损坏
    A006 = "ARTIFACT_TOO_LARGE"                # Artifact 过大

    # 数据库错误 (DXXX)
    D001 = "DATABASE_CONNECTION_FAILED"        # 数据库连接失败
    D002 = "DATABASE_QUERY_FAILED"             # 查询失败
    D003 = "DATABASE_CONSTRAINT_VIOLATION"     # 约束违反
    D004 = "DATABASE_TIMEOUT"                   # 数据库超时

    # 外部服务错误 (EXXX)
    E001 = "TTS_SERVICE_UNAVAILABLE"           # TTS 服务不可用
    E002 = "ASR_SERVICE_UNAVAILABLE"           # ASR 服务不可用
    E003 = "TMDB_API_ERROR"                     # TMDB API 错误
    E004 = "NETWORK_ERROR"                      # 网络错误

    # 用户错误 (UXXX)
    U001 = "INVALID_INPUT"                      # 无效输入
    U002 = "INSUFFICIENT_PERMISSIONS"          # 权限不足
    U003 = "USER_CANCELLED"                     # 用户取消
```

## 重试策略

### 1. 重试策略配置

```python
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class RetryPolicy:
    """重试策略配置"""
    max_retries: int = 3                      # 最大重试次数
    initial_delay: float = 1.0                # 初始延迟（秒）
    max_delay: float = 60.0                   # 最大延迟（秒）
    multiplier: float = 2.0                   # 延迟倍数

    # 重试条件
    retryable_errors: list = None             # 可重试的错误代码列表

    # 特殊处理
    on_retry: Optional[Callable] = None       # 每次重试前的回调
    on_give_up: Optional[Callable] = None     # 放弃重试时的回调

    def __post_init__(self):
        if self.retryable_errors is None:
            # 默认可重试的错误
            self.retryable_errors = [
                ErrorCodes.W003,  # Worker 超时
                ErrorCodes.W004,  # Worker 离线
                ErrorCodes.S001,  # 没有可用 Worker
                ErrorCodes.A002,  # 下载失败
                ErrorCodes.A003,  # 上传失败
                ErrorCodes.D001,  # 数据库连接失败
                ErrorCodes.D004,  # 数据库超时
                ErrorCodes.E004,  # 网络错误
            ]
```

### 2. 重试执行器

```python
import asyncio
from loguru import logger

class RetryExecutor:
    """重试执行器"""

    def __init__(self, policy: RetryPolicy):
        self.policy = policy

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """执行函数，根据策略重试

        Args:
            func: 要执行的异步函数
            *args, **kwargs: 函数参数

        Returns:
            函数返回值

        Raises:
            最后一次执行的异常
        """
        last_exception = None
        delay = self.policy.initial_delay

        for attempt in range(self.policy.max_retries + 1):
            try:
                # 执行函数
                result = await func(*args, **kwargs)
                return result

            except Exception as e:
                last_exception = e
                error_code = getattr(e, 'error_code', None)

                # 检查是否可重试
                if not self._is_retryable(error_code):
                    logger.warning(f"Error {error_code} is not retryable")
                    raise

                # 回调
                if self.policy.on_retry:
                    await self.policy.on_retry(attempt, e)

                # 最后一次尝试失败
                if attempt == self.policy.max_retries:
                    if self.policy.on_give_up:
                        await self.policy.on_give_up(attempt, e)
                    raise

                # 等待后重试
                logger.info(
                    f"Retry {attempt + 1}/{self.policy.max_retries} "
                    f"after {delay}s (error: {error_code})"
                )
                await asyncio.sleep(delay)

                # 计算下次延迟（指数退避）
                delay = min(
                    delay * self.policy.multiplier,
                    self.policy.max_delay
                )

        raise last_exception

    def _is_retryable(self, error_code: Optional[str]) -> bool:
        """检查错误是否可重试"""
        if error_code is None:
            return True  # 未知错误，尝试重试
        return error_code in self.policy.retryable_errors

    def calculate_delay(self, attempt: int) -> float:
        """计算重试延迟（带抖动）"""
        base_delay = min(
            self.policy.initial_delay * (self.policy.multiplier ** attempt),
            self.policy.max_delay
        )
        # 添加随机抖动（±25%）
        import random
        jitter = base_delay * 0.25 * (random.random() * 2 - 1)
        return base_delay + jitter
```

### 3. 错误处理器

```python
class ErrorHandler:
    """错误处理器"""

    def __init__(self, db, notification_service):
        self.db = db
        self.notification = notification_service

    async def handle_error(self, error: SystemError) -> None:
        """处理错误

        Args:
            error: 系统错误
        """
        # 1. 记录错误
        await self._log_error(error)

        # 2. 检查是否需要自动重试
        if error.is_retryable and error.retry_count < error.max_retries:
            await self._schedule_retry(error)
            return

        # 3. 根据严重程度处理
        if error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            await self._handle_critical_error(error)
        elif error.severity == ErrorSeverity.ERROR:
            await self._handle_error(error)
        else:
            await self._handle_warning(error)

    async def _log_error(self, error: SystemError) -> None:
        """记录错误到数据库"""
        await self.db.execute(
            """
            INSERT INTO error_log (
                error_id, error_code, error_type, message,
                source, recoverability, severity,
                context, job_id, worker_id, project_id,
                timestamp, is_handled
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
            error.error_id, error.error_code, error.error_type,
            error.message, error.source.value, error.recoverability.value,
            error.severity.value, error.context, error.job_id,
            error.worker_id, error.project_id, error.timestamp,
            error.is_handled
        )

    async def _schedule_retry(self, error: SystemError) -> None:
        """安排重试"""
        # 计算重试延迟
        policy = self._get_retry_policy(error.error_code)
        executor = RetryExecutor(policy)
        delay = executor.calculate_delay(error.retry_count)

        # 更新错误状态
        error.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
        error.retry_count += 1

        # 保存到数据库
        await self.db.execute(
            """
            UPDATE jobs
            SET status = 'retrying',
                retry_count = $1,
                next_retry_at = $2
            WHERE id = $3
            """,
            error.retry_count, error.next_retry_at, error.job_id
        )

        # 调度重试任务
        await self._schedule_task(
            'retry_job',
            error.job_id,
            delay=delay
        )

        logger.info(
            f"Scheduled retry for job {error.job_id} "
            f"at {error.next_retry_at}"
        )

    async def _handle_critical_error(self, error: SystemError) -> None:
        """处理严重错误"""
        # 1. 立即通知管理员
        await self.notification.send_alert(
            severity="critical",
            message=f"Critical error: {error.message}",
            context=error.context
        )

        # 2. 可能需要紧急停止相关任务
        if error.job_id:
            await self._cancel_related_jobs(error.job_id)

        # 3. 标记需要人工介入
        await self._mark_manual_intervention(error)

    async def _handle_error(self, error: SystemError) -> None:
        """处理普通错误"""
        # 1. 更新 Job 状态
        if error.job_id:
            await self.db.execute(
                """
                UPDATE jobs
                SET status = 'failed',
                    error_message = $1,
                    completed_at = NOW()
                WHERE id = $2
                """,
                error.message, error.job_id
            )

        # 2. 通知用户
        await self.notification.send_notification(
            user_id=error.context.get('user_id'),
            message=f"Job failed: {error.message}",
            job_id=error.job_id
        )

    def _get_retry_policy(self, error_code: str) -> RetryPolicy:
        """根据错误代码获取重试策略"""
        # 临时性错误：快速重试
        if error_code in [ErrorCodes.W003, ErrorCodes.D004]:
            return RetryPolicy(max_retries=5, initial_delay=2, max_delay=30)

        # 资源错误：较慢重试
        if error_code in [ErrorCodes.W002, ErrorCodes.S001]:
            return RetryPolicy(max_retries=10, initial_delay=10, max_delay=300)

        # 网络错误：中等重试
        if error_code in [ErrorCodes.E004, ErrorCodes.A002]:
            return RetryPolicy(max_retries=3, initial_delay=5, max_delay=60)

        # 默认策略
        return RetryPolicy()
```

## 降级策略

### 1. 服务降级

```python
class DegradationStrategy:
    """服务降级策略"""

    async def handle_tts_failure(self, error: SystemError) -> Dict:
        """TTS 失败时的降级策略"""
        # 1. 尝试备用 TTS 模型
        if error.context.get('tts_model') == 'cosyvoice':
            # 尝试 F5-TTS
            return {
                "action": "retry_with_backup",
                "backup_model": "f5-tts",
                "config": error.context
            }

        # 2. 如果备用模型也失败，返回原始音频（如果可用）
        if error.artifact_id:
            return {
                "action": "use_original_audio",
                "artifact_id": error.artifact_id
            }

        # 3. 最后降级：静音或跳过
        return {
            "action": "skip",
            "reason": "No backup available"
        }

    async def handle_asr_failure(self, error: SystemError) -> Dict:
        """ASR 失败时的降级策略"""
        # 1. 使用字幕时间戳
        if error.context.get('subtitle_available'):
            return {
                "action": "use_subtitle_timestamps"
            }

        # 2. 使用固定时间间隔
        return {
            "action": "use_fixed_intervals",
            "interval_ms": 5000
        }
```

### 2. 熔断器

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"       # 正常工作
    OPEN = "open"           # 熔断打开，拒绝请求
    HALF_OPEN = "half_open" # 半开，尝试恢复

class CircuitBreaker:
    """熔断器"""

    def __init__(
        self,
        failure_threshold: int = 5,      # 失败阈值
        success_threshold: int = 2,      # 恢复阈值
        timeout: int = 60                 # 熔断超时（秒）
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None

    async def call(self, func: Callable, *args, **kwargs):
        """通过熔断器调用函数

        Args:
            func: 要调用的函数

        Returns:
            函数返回值

        Raises:
            CircuitBreakerOpenError: 熔断器打开时
        """
        # 检查熔断器状态
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN, will reset at {self.opened_at + timedelta(seconds=self.timeout)}"
                )

        try:
            # 调用函数
            result = await func(*args, **kwargs)

            # 成功：重置失败计数
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self._reset()
                    logger.info("Circuit breaker reset to CLOSED state")

            return result

        except Exception as e:
            # 失败：增加失败计数
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()

            # 达到阈值：打开熔断器
            if self.failure_count >= self.failure_threshold:
                self._trip()
                logger.warning(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )

            raise

    def _should_attempt_reset(self) -> bool:
        """是否应该尝试重置"""
        return (
            self.opened_at and
            datetime.utcnow() >= self.opened_at + timedelta(seconds=self.timeout)
        )

    def _trip(self):
        """打开熔断器"""
        self.state = CircuitState.OPEN
        self.opened_at = datetime.utcnow()
        self.success_count = 0

    def _reset(self):
        """重置熔断器"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None
```

## 错误监控和告警

### 1. 错误统计

```python
@dataclass
class ErrorStatistics:
    """错误统计"""
    total_errors: int = 0
    by_code: Dict[str, int] = None      # 按错误代码统计
    by_source: Dict[str, int] = None    # 按来源统计
    by_severity: Dict[str, int] = None  # 按严重程度统计

    retry_rate: float = 0.0             # 重试率
    recovery_rate: float = 0.0          # 恢复率

    top_errors: List[Tuple[str, int]] = None  # 最常见的错误

class ErrorMonitor:
    """错误监控"""

    async def get_statistics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> ErrorStatistics:
        """获取错误统计"""
        # 从数据库查询
        stats = await self.db.fetch_one(
            """
            SELECT
                COUNT(*) as total_errors,
                COUNT(DISTINCT error_code) as unique_errors
            FROM error_log
            WHERE timestamp BETWEEN $1 AND $2
            """,
            start_time, end_time
        )

        # 按错误代码统计
        by_code = await self.db.fetch(
            """
            SELECT error_code, COUNT(*) as count
            FROM error_log
            WHERE timestamp BETWEEN $1 AND $2
            GROUP BY error_code
            ORDER BY count DESC
            LIMIT 10
            """,
            start_time, end_time
        )

        return ErrorStatistics(
            total_errors=stats['total_errors'],
            by_code={row['error_code']: row['count'] for row in by_code},
            top_errors=[(row['error_code'], row['count']) for row in by_code]
        )
```

### 2. 告警规则

```python
class AlertRule:
    """告警规则"""

    def __init__(self):
        self.rules = [
            # 错误率告警
            {
                "name": "high_error_rate",
                "condition": lambda stats: stats.total_errors > 100,
                "severity": "warning",
                "message": "High error rate detected"
            },

            # 严重错误告警
            {
                "name": "critical_error",
                "condition": lambda stats: any(
                    code.startswith('F') or code.startswith('C')
                    for code in stats.by_code.keys()
                ),
                "severity": "critical",
                "message": "Critical error occurred"
            },

            # Worker 离线告警
            {
                "name": "worker_offline",
                "condition": lambda stats: stats.by_source.get(
                    ErrorSource.WORKER_OFFLINE.value, 0
                ) > 3,
                "severity": "warning",
                "message": "Multiple workers offline"
            }
        ]
```

## 最佳实践

1. **快速失败**: 对于不可恢复的错误，立即失败
2. **优雅降级**: 提供降级方案，而非完全失败
3. **重试幂等**: 确保重试操作是幂等的
4. **上下文丰富**: 错误信息包含足够的上下文
5. **监控可见**: 所有关键错误都应该可见和可追踪
6. **文档更新**: 错误代码和策略文档化

## 后续决策

- 是否需要错误分类学（更细粒度的分类）
- 错误数据的保留策略
- 是否需要实时错误流处理
