# ADR 0008: 监控和日志系统

## 状态

设计中

## 上下文

影视AI配音平台是一个复杂的分布式系统，需要完善的监控和日志系统来确保：
1. 系统健康状态可见
2. 问题快速定位和诊断
3. 性能优化支持
4. 运营数据分析

## 监控架构

```
┌─────────────────────────────────────────────────────────────────┐
│                          监控层                                  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   指标采集    │  │    日志采集   │  │    追踪采集   │         │
│  │  (Metrics)   │  │   (Logging)  │  │  (Tracing)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                  │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    消息总线 (Kafka/Redis)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│         ┌──────────────────┼──────────────────┐                 │
│         ▼                  ▼                  ▼                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Prometheus  │  │   Loki/ELK   │  │    Jaeger    │       │
│  │  (指标存储)   │  │   (日志存储)  │  │   (追踪)     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                      Grafana                               │  │
│  │                    (统一仪表盘)                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 指标监控

### 1. 指标分类

```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import datetime

class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"       # 计数器（只增不减）
    GAUGE = "gauge"          # 仪表盘（可增可减）
    HISTOGRAM = "histogram"   # 直方图（分布）
    SUMMARY = "summary"      # 摘要（统计）

class MetricCategory(Enum):
    """指标分类"""
    # 系统指标
    SYSTEM = "system"         # 系统资源
    PROCESS = "process"       # 进程指标

    # 应用指标
    API = "api"              # API 指标
    WORKER = "worker"        # Worker 指标
    JOB = "job"              # Job 指标
    ARTIFACT = "artifact"    # Artifact 指标

    # 业务指标
    PROJECT = "project"      # 项目指标
    CHARACTER = "character"   # 人物指标
    VOICE = "voice"          # 音色指标

    # 外部依赖
    DATABASE = "database"     # 数据库指标
    CACHE = "cache"          # 缓存指标
    STORAGE = "storage"      # 存储指标
    EXTERNAL_API = "external_api"  # 外部API指标

@dataclass
class MetricDefinition:
    """指标定义"""
    name: str                  # 指标名称
    type: MetricType          # 指标类型
    category: MetricCategory  # 指标分类
    description: str          # 描述
    labels: List[str]         # 标签维度

    # 阈值配置
    thresholds: Dict[str, float] = None  # 警告阈值

    # 聚合配置
    aggregation: str = "avg"   # 聚合方式: sum, avg, max, min

# 核心指标定义
CORE_METRICS = {
    # 系统资源
    "system_cpu_usage": MetricDefinition(
        name="system_cpu_usage",
        type=MetricType.GAUGE,
        category=MetricCategory.SYSTEM,
        description="系统 CPU 使用率",
        labels=["host", "worker_type"],
        thresholds={"warning": 0.8, "critical": 0.95}
    ),

    "system_memory_usage": MetricDefinition(
        name="system_memory_usage",
        type=MetricType.GAUGE,
        category=MetricCategory.SYSTEM,
        description="系统内存使用率",
        labels=["host", "worker_type"],
        thresholds={"warning": 0.85, "critical": 0.95}
    ),

    "system_disk_usage": MetricDefinition(
        name="system_disk_usage",
        type=MetricType.GAUGE,
        category=MetricCategory.SYSTEM,
        description="系统磁盘使用率",
        labels=["host", "mount_point"],
        thresholds={"warning": 0.85, "critical": 0.95}
    ),

    # API 指标
    "api_requests_total": MetricDefinition(
        name="api_requests_total",
        type=MetricType.COUNTER,
        category=MetricCategory.API,
        description="API 请求总数",
        labels=["endpoint", "method", "status"]
    ),

    "api_request_duration": MetricDefinition(
        name="api_request_duration",
        type=MetricType.HISTOGRAM,
        category=MetricCategory.API,
        description="API 请求耗时",
        labels=["endpoint", "method"],
        thresholds={"warning": 1.0, "critical": 5.0}  # 秒
    ),

    "api_request_errors": MetricDefinition(
        name="api_request_errors",
        type=MetricType.COUNTER,
        category=MetricCategory.API,
        description="API 错误数",
        labels=["endpoint", "method", "error_code"]
    ),

    # Job 指标
    "job_duration": MetricDefinition(
        name="job_duration",
        type=MetricType.HISTOGRAM,
        category=MetricCategory.JOB,
        description="Job 执行时长",
        labels=["module_id", "worker_type"]
    ),

    "job_queue_size": MetricDefinition(
        name="job_queue_size",
        type=MetricType.GAUGE,
        category=MetricCategory.JOB,
        description="Job 队列大小",
        labels=["module_id", "priority"]
    ),

    "job_throughput": MetricDefinition(
        name="job_throughput",
        type=MetricType.GAUGE,
        category=MetricCategory.JOB,
        description="Job 吞吐量 (jobs/min)",
        labels=["module_id", "status"]
    ),

    # Worker 指标
    "worker_status": MetricDefinition(
        name="worker_status",
        type=MetricType.GAUGE,
        category=MetricCategory.WORKER,
        description="Worker 状态 (0=offline, 1=idle, 2=busy)",
        labels=["worker_id", "worker_type"]
    ),

    "worker_job_count": MetricDefinition(
        name="worker_job_count",
        type=MetricType.GAUGE,
        category=MetricCategory.WORKER,
        description="Worker 当前 Job 数",
        labels=["worker_id", "module_id"]
    ),

    # Artifact 指标
    "artifact_size_bytes": MetricDefinition(
        name="artifact_size_bytes",
        type=MetricType.HISTOGRAM,
        category=MetricCategory.ARTIFACT,
        description="Artifact 大小",
        labels=["type", "project_id"]
    ),

    "artifact_upload_duration": MetricDefinition(
        name="artifact_upload_duration",
        type=MetricType.HISTOGRAM,
        category=MetricCategory.ARTIFACT,
        description="Artifact 上传耗时",
        labels=["type", "size_range"]
    ),

    # 数据库指标
    "db_query_duration": MetricDefinition(
        name="db_query_duration",
        type=MetricType.HISTOGRAM,
        category=MetricCategory.DATABASE,
        description="数据库查询耗时",
        labels=["query_type", "table"]
    ),

    "db_connections": MetricDefinition(
        name="db_connections",
        type=MetricType.GAUGE,
        category=MetricCategory.DATABASE,
        description="数据库连接数",
        labels=["state"],  # idle, active, total
        thresholds={"warning": 80, "critical": 95}
    ),

    # 缓存指标
    "cache_hit_rate": MetricDefinition(
        name="cache_hit_rate",
        type=MetricType.GAUGE,
        category=MetricCategory.CACHE,
        description="缓存命中率",
        labels=["cache_type"],
        thresholds={"warning": 0.7, "critical": 0.5}
    ),

    # 业务指标
    "project_completion_rate": MetricDefinition(
        name="project_completion_rate",
        type=MetricType.GAUGE,
        category=MetricCategory.PROJECT,
        description="项目完成率",
        labels=["time_range"]
    ),

    "voice_synthesis_quality": MetricDefinition(
        name="voice_synthesis_quality",
        type=MetricType.GAUGE,
        category=MetricCategory.VOICE,
        description="语音合成质量评分",
        labels=["character_id", "voice_profile"]
    ),
}
```

### 2. 指标采集

```python
from prometheus_client import Counter, Gauge, Histogram, Summary
import psutil
import time
from functools import wraps

class MetricsCollector:
    """指标采集器"""

    def __init__(self):
        self.metrics = {}
        self._init_prometheus_metrics()

    def _init_prometheus_metrics(self):
        """初始化 Prometheus 指标"""
        # 系统指标
        self.metrics['cpu_usage'] = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage',
            ['host', 'worker_type']
        )

        self.metrics['memory_usage'] = Gauge(
            'system_memory_usage_percent',
            'System memory usage percentage',
            ['host', 'worker_type']
        )

        # API 指标
        self.metrics['api_requests'] = Counter(
            'api_requests_total',
            'Total API requests',
            ['endpoint', 'method', 'status']
        )

        self.metrics['api_duration'] = Histogram(
            'api_request_duration_seconds',
            'API request duration',
            ['endpoint', 'method'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
        )

        # Job 指标
        self.metrics['job_duration'] = Histogram(
            'job_duration_seconds',
            'Job execution duration',
            ['module_id', 'worker_type'],
            buckets=(60, 300, 600, 1800, 3600)  # 1min-1hour
        )

        self.metrics['job_queue_size'] = Gauge(
            'job_queue_size',
            'Current job queue size',
            ['module_id', 'priority']
        )

    async def collect_system_metrics(self, host: str, worker_type: str = None):
        """采集系统指标"""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        self.metrics['cpu_usage'].labels(
            host=host,
            worker_type=worker_type or 'unknown'
        ).set(cpu_percent)

        # 内存
        memory = psutil.virtual_memory()
        self.metrics['memory_usage'].labels(
            host=host,
            worker_type=worker_type or 'unknown'
        ).set(memory.percent)

        # 磁盘
        disk = psutil.disk_usage('/')
        # 可以添加磁盘使用率指标

    async def collect_job_metrics(self, db):
        """采集 Job 指标"""
        # 队列大小
        queue_stats = await db.fetch(
            """
            SELECT module_id, priority, COUNT(*) as count
            FROM jobs
            WHERE status IN ('pending', 'waiting', 'ready')
            GROUP BY module_id, priority
            """
        )

        for row in queue_stats:
            self.metrics['job_queue_size'].labels(
                module_id=row['module_id'],
                priority=row['priority']
            ).set(row['count'])

    def track_api_request(self, endpoint: str, method: str):
        """API 请求追踪装饰器"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                status = "success"

                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = "error"
                    raise
                finally:
                    duration = time.time() - start_time

                    # 记录请求
                    self.metrics['api_requests'].labels(
                        endpoint=endpoint,
                        method=method,
                        status=status
                    ).inc()

                    # 记录耗时
                    self.metrics['api_duration'].labels(
                        endpoint=endpoint,
                        method=method
                    ).observe(duration)

            return wrapper
        return decorator
```

### 3. 指标暴露

```python
from prometheus_client import start_http_server
from prometheus_client import REGISTRY

class MetricsExporter:
    """指标导出器"""

    def __init__(self, port: int = 9090):
        self.port = port

    async def start(self):
        """启动 Prometheus 指标服务器"""
        start_http_server(self.port)
        logger.info(f"Metrics exporter started on port {self.port}")

    async def export_custom_metrics(self, metrics: Dict[str, Any]):
        """导出自定义指标"""
        for metric_name, value in metrics.items():
            # 可以使用 Gauge 或 Counter 记录
            pass
```

## 日志系统

### 1. 日志分类

```python
class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"       # 调试信息
    INFO = "info"         # 一般信息
    WARNING = "warning"    # 警告
    ERROR = "error"       # 错误
    CRITICAL = "critical" # 严重

class LogCategory(Enum):
    """日志分类"""
    # 系统日志
    SYSTEM = "system"           # 系统启动、关闭等
    API = "api"                # API 请求
    DATABASE = "database"       # 数据库操作
    WORKER = "worker"          # Worker 操作
    SCHEDULER = "scheduler"    # 调度器操作

    # 业务日志
    JOB = "job"                # Job 执行
    ARTIFACT = "artifact"       # Artifact 操作
    PROJECT = "project"        # 项目操作

    # 审计日志
    AUDIT = "audit"            # 用户操作审计
    SECURITY = "security"      # 安全相关

    # 性能日志
    PERFORMANCE = "performance" # 性能数据
```

### 2. 日志格式

```python
import json
from datetime import datetime
from typing import Dict, Any, Optional

class LogEntry:
    """日志条目"""

    def __init__(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        **kwargs
    ):
        self.timestamp = datetime.utcnow()
        self.level = level
        self.category = category
        self.message = message
        self.context = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category.value,
            "message": self.message,
            **self.context
        }

    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

# 使用示例
log_entry = LogEntry(
    level=LogLevel.INFO,
    category=LogCategory.JOB,
    message="Job completed successfully",
    job_id="uuid",
    module_id="M09",
    duration_seconds=1800,
    worker_id="uuid"
)
```

### 3. 日志采集

```python
from loguru import logger
import sys

class LogCollector:
    """日志采集器"""

    def __init__(self):
        self._setup_logger()

    def _setup_logger(self):
        """配置日志器"""
        # 移除默认处理器
        logger.remove()

        # 添加控制台处理器（开发环境）
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG"
        )

        # 添加文件处理器（持久化）
        logger.add(
            "logs/app_{time:YYYY-MM-DD}.log",
            rotation="00:00",        # 每天轮转
            retention="30 days",     # 保留 30 天
            compression="zip",       # 压缩旧日志
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="INFO"
        )

        # 添加 Loki 处理器（集中日志）
        logger.add(
            self._loki_handler,
            level="INFO",
            serialize=True  # JSON 格式
        )

    def _loki_handler(self, message):
        """Loki 日志处理器"""
        # 发送到 Loki
        # 这里简化处理，实际应该使用 Loki 客户端
        pass

    async def log_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration: float,
        user_id: Optional[str] = None
    ):
        """记录 API 请求"""
        logger.info(
            "API request",
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration=duration,
            user_id=user_id
        )

    async def log_job_event(
        self,
        job_id: str,
        event: str,
        **kwargs
    ):
        """记录 Job 事件"""
        logger.info(
            f"Job {event}",
            job_id=job_id,
            event=event,
            **kwargs
        )

    async def log_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ):
        """记录错误"""
        logger.error(
            f"Error: {str(error)}",
            error_type=type(error).__name__,
            **context
        )
```

### 4. 结构化日志

```python
class StructuredLogger:
    """结构化日志器"""

    def __init__(self, service_name: str):
        self.service_name = service_name

    def log(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        **context
    ):
        """记录结构化日志"""
        log_entry = {
            "service": self.service_name,
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "category": category.value,
            "message": message,
            "context": context
        }

        # 输出到标准输出（JSON 格式）
        print(json.dumps(log_entry))

        # 同时发送到日志收集系统
        # asyncio.create_task(send_to_loki(log_entry))
```

## 分布式追踪

### 1. 追踪配置

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

class TracingSetup:
    """追踪配置"""

    def __init__(self, service_name: str, jaeger_endpoint: str):
        self.service_name = service_name
        self.jaeger_endpoint = jaeger_endpoint

    def setup(self):
        """设置追踪"""
        # 创建资源
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": "1.0.0"
        })

        # 创建追踪器提供者
        provider = TracerProvider(resource=resource)

        # 配置 Jaeger 导出器
        jaeger_exporter = JaegerExporter(
            agent_host_name=self.jaeger_endpoint.split(':')[0],
            agent_port=int(self.jaeger_endpoint.split(':')[1]),
        )

        # 添加批量处理器
        provider.add_span_processor(
            BatchSpanProcessor(jaeger_exporter)
        )

        # 设置全局追踪器
        trace.set_tracer_provider(provider)

        # 自动追踪
        self._auto_instrument()

    def _auto_instrument(self):
        """自动追踪常用库"""
        # FastAPI
        FastAPIInstrumentor().instrument()

        # HTTPX
        HTTPXClientInstrumentor().instrument()
```

### 2. 手动追踪

```python
from opentelemetry import trace

class ManualTracer:
    """手动追踪器"""

    def __init__(self):
        self.tracer = trace.get_tracer(__name__)

    def trace_job_execution(
        self,
        job_id: str,
        module_id: str,
        func: Callable
    ):
        """追踪 Job 执行"""
        with self.tracer.start_as_current_span(
            f"job_execution",
            attributes={
                "job_id": job_id,
                "module_id": module_id
            }
        ) as span:
            try:
                result = func()

                # 记录成功
                span.set_attribute("status", "success")
                return result

            except Exception as e:
                # 记录错误
                span.set_attribute("status", "error")
                span.set_attribute("error.message", str(e))
                span.record_exception(e)
                raise

    def trace_artifact_operation(
        self,
        operation: str,
        artifact_id: str,
        func: Callable
    ):
        """追踪 Artifact 操作"""
        with self.tracer.start_as_current_span(
            f"artifact_{operation}",
            attributes={
                "operation": operation,
                "artifact_id": artifact_id
            }
       ):
            return func()
```

## 仪表盘

### 1. 核心仪表盘

```python
DASHBOARD_CONFIGS = {
    "overview": {
        "title": "系统概览",
        "panels": [
            {
                "title": "系统健康",
                "type": "stat",
                "targets": [
                    "system_cpu_usage",
                    "system_memory_usage",
                    "worker_status"
                ]
            },
            {
                "title": "API 请求速率",
                "type": "graph",
                "targets": [
                    "rate(api_requests_total[5m])"
                ]
            },
            {
                "title": "Job 吞吐量",
                "type": "graph",
                "targets": [
                    "rate(job_completed_total[5m])"
                ]
            }
        ]
    },

    "jobs": {
        "title": "Job 监控",
        "panels": [
            {
                "title": "Job 队列大小",
                "type": "graph",
                "targets": [
                    "job_queue_size"
                ]
            },
            {
                "title": "Job 执行时长分布",
                "type": "heatmap",
                "targets": [
                    "histogram_quantile(0.95, job_duration_seconds)"
                ]
            },
            {
                "title": "Job 失败率",
                "type": "gauge",
                "targets": [
                    "rate(job_failed_total[5m]) / rate(job_completed_total[5m])"
                ]
            }
        ]
    },

    "workers": {
        "title": "Worker 监控",
        "panels": [
            {
                "title": "Worker 状态分布",
                "type": "pie",
                "targets": [
                    "count by (status) (worker_status)"
                ]
            },
            {
                "title": "Worker 资源使用",
                "type": "heatmap",
                "targets": [
                    "worker_cpu_usage",
                    "worker_memory_usage"
                ]
            }
        ]
    },

    "artifacts": {
        "title": "Artifact 监控",
        "panels": [
            {
                "title": "Artifact 上传速率",
                "type": "graph",
                "targets": [
                    "rate(artifact_upload_total[5m])"
                ]
            },
            {
                "title": "Artifact 存储使用",
                "type": "gauge",
                "targets": [
                    "artifact_storage_bytes"
                ]
            }
        ]
    }
}
```

### 2. 告警规则

```python
ALERT_RULES = """
groups:
  - name: system_alerts
    rules:
      # 系统资源告警
      - alert: HighCPUUsage
        expr: system_cpu_usage_percent > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is {{ $value }}% on {{ $labels.host }}"

      - alert: HighMemoryUsage
        expr: system_memory_usage_percent > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is {{ $value }}% on {{ $labels.host }}"

      # API 告警
      - alert: HighAPIErrorRate
        expr: rate(api_requests_total{status="error"}[5m]) / rate(api_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API error rate"
          description: "API error rate is {{ $value }}"

      # Job 告警
      - alert: JobQueueBacklog
        expr: sum(job_queue_size) > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Job queue backlog"
          description: "Job queue size is {{ $value }}"

      - alert: WorkerOffline
        expr: count(worker_status == 0) > count(worker_status) * 0.3
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Multiple workers offline"
          description: "{{ $value }} workers are offline"
"""
```

## 最佳实践

1. **采样**: 对高频事件进行采样
2. **聚合**: 在源头进行聚合，减少传输量
3. **标签**: 标签维度不宜过多（<10个）
4. **保留**: 根据合规要求设置日志保留期
5. **脱敏**: 敏感信息脱敏后再记录
6. **查询**: 提供预定义查询，方便快速定位问题

## 后续决策

- 日志存储选择（Loki vs ELK）
- 是否需要实时告警（即时通知）
- 监控数据的备份和归档策略
- 是否需要 APM（应用性能监控）
