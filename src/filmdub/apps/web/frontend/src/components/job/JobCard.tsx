/** 任务卡片组件 */
import { JobStatus, JobResponse } from '../../services/jobAPI';
import {
  Clock,
  Play,
  Pause,
  XCircle,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  MoreVertical,
} from 'lucide-react';

interface JobCardProps {
  job: JobResponse;
  onPause?: () => void;
  onResume?: () => void;
  onCancel?: () => void;
  onRetry?: () => void;
  onViewDetails?: () => void;
  showActions?: boolean;
}

export function JobCard({
  job,
  onPause,
  onResume,
  onCancel,
  onRetry,
  onViewDetails,
  showActions = true,
}: JobCardProps) {
  const getStatusIcon = (status: JobStatus) => {
    switch (status) {
      case 'pending':
        return <Clock className="w-5 h-5 text-gray-400" />;
      case 'scheduled':
        return <Clock className="w-5 h-5 text-blue-400" />;
      case 'running':
        return <Play className="w-5 h-5 text-green-500 animate-pulse" />;
      case 'waiting':
        return <Pause className="w-5 h-5 text-yellow-500" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'cancelled':
        return <XCircle className="w-5 h-5 text-gray-400" />;
      case 'retrying':
        return <RefreshCw className="w-5 h-5 text-orange-500 animate-spin" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusText = (status: JobStatus) => {
    const statusMap: Record<JobStatus, string> = {
      pending: '等待中',
      scheduled: '已调度',
      running: '运行中',
      waiting: '已暂停',
      completed: '已完成',
      failed: '失败',
      cancelled: '已取消',
      retrying: '重试中',
    };
    return statusMap[status] || status;
  };

  const getStatusColor = (status: JobStatus) => {
    switch (status) {
      case 'pending':
        return 'bg-gray-100 text-gray-700';
      case 'scheduled':
        return 'bg-blue-100 text-blue-700';
      case 'running':
        return 'bg-green-100 text-green-700';
      case 'waiting':
        return 'bg-yellow-100 text-yellow-700';
      case 'completed':
        return 'bg-green-100 text-green-700';
      case 'failed':
        return 'bg-red-100 text-red-700';
      case 'cancelled':
        return 'bg-gray-100 text-gray-700';
      case 'retrying':
        return 'bg-orange-100 text-orange-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const canPause = ['scheduled', 'running', 'retrying'].includes(job.status);
  const canResume = job.status === 'waiting';
  const canCancel = ['pending', 'scheduled', 'running', 'retrying'].includes(job.status);
  const canRetry = job.status === 'failed' && job.retry_count < job.max_retries;

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const calculateDuration = () => {
    if (!job.started_at || !job.completed_at) return null;
    const start = new Date(job.started_at).getTime();
    const end = new Date(job.completed_at).getTime();
    const seconds = Math.floor((end - start) / 1000);

    if (seconds < 60) return `${seconds}秒`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`;
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}小时${minutes}分`;
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      {/* 头部 */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-3 flex-1 min-w-0">
          {getStatusIcon(job.status)}

          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-medium text-gray-900 truncate">
              {job.name}
            </h3>
            <div className="flex items-center space-x-2 mt-1">
              <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(job.status)}`}>
                {getStatusText(job.status)}
              </span>
              {job.module_id && (
                <span className="text-xs text-gray-500">
                  {job.module_id}
                </span>
              )}
            </div>
          </div>
        </div>

        {showActions && (
          <div className="flex items-center space-x-1 ml-2">
            {canPause && onPause && (
              <button
                onClick={() => onPause()}
                className="p-1.5 text-gray-400 hover:text-yellow-600 hover:bg-yellow-50 rounded transition-colors"
                title="暂停"
              >
                <Pause className="w-4 h-4" />
              </button>
            )}

            {canResume && onResume && (
              <button
                onClick={() => onResume()}
                className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                title="恢复"
              >
                <Play className="w-4 h-4" />
              </button>
            )}

            {canCancel && onCancel && (
              <button
                onClick={() => onCancel()}
                className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                title="取消"
              >
                <XCircle className="w-4 h-4" />
              </button>
            )}

            {canRetry && onRetry && (
              <button
                onClick={() => onRetry()}
                className="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors"
                title="重试"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            )}

            {onViewDetails && (
              <button
                onClick={() => onViewDetails()}
                className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                title="查看详情"
              >
                <MoreVertical className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>

      {/* 描述 */}
      {job.description && (
        <p className="text-sm text-gray-600 mb-3 line-clamp-2">
          {job.description}
        </p>
      )}

      {/* 错误信息 */}
      {job.error_message && (
        <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded">
          <p className="text-xs text-red-800">{job.error_message}</p>
        </div>
      )}

      {/* 元数据 */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center space-x-3">
          <span>创建于 {formatDate(job.created_at)}</span>
          {job.started_at && !job.completed_at && (
            <span>运行中...</span>
          )}
          {calculateDuration() && (
            <span>耗时 {calculateDuration()}</span>
          )}
        </div>

        {job.retry_count > 0 && (
          <span>
            重试 {job.retry_count}/{job.max_retries}
          </span>
        )}
      </div>
    </div>
  );
}
