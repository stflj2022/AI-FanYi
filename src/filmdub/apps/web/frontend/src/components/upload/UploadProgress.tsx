/** 上传进度条组件 */
import { Upload, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';
import { UploadStatus } from '../../services/uploadAPI';

interface UploadProgressProps {
  filename: string;
  progress: number;
  status: UploadStatus;
  fileSize?: number;
  speed?: number;
  estimatedTime?: number;
  error?: string;
  onCancel?: () => void;
  onRetry?: () => void;
}

export function UploadProgress({
  filename,
  progress,
  status,
  fileSize,
  speed,
  estimatedTime,
  error,
  onCancel,
  onRetry,
}: UploadProgressProps) {
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatSpeed = (bytesPerSec: number): string => {
    return `${formatFileSize(bytesPerSec)}/s`;
  };

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${Math.round(seconds)}秒`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}分${Math.round(seconds % 60)}秒`;
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}小时${minutes}分`;
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'pending':
        return <Clock className="w-5 h-5 text-gray-400" />;
      case 'uploading':
        return <Upload className="w-5 h-5 text-blue-500 animate-pulse" />;
      case 'ready':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'pending':
        return '等待中';
      case 'uploading':
        return '上传中';
      case 'ready':
        return '完成';
      case 'failed':
        return '失败';
      default:
        return '';
    }
  };

  return (
    <div className="w-full bg-white border border-gray-200 rounded-lg p-4 space-y-3">
      {/* 文件信息行 */}
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-3 flex-1 min-w-0">
          {getStatusIcon()}

          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {filename}
            </p>
            <div className="flex items-center space-x-2 mt-1">
              <span className="text-xs text-gray-500">
                {fileSize && formatFileSize(fileSize)}
              </span>
              <span className="text-xs text-gray-300">•</span>
              <span className="text-xs text-gray-500">{getStatusText()}</span>
              {status === 'uploading' && (
                <>
                  <span className="text-xs text-gray-300">•</span>
                  <span className="text-xs text-blue-600 font-medium">
                    {progress.toFixed(1)}%
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* 操作按钮 */}
        {status === 'uploading' && onCancel && (
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            title="取消上传"
          >
            <XCircle className="w-5 h-5" />
          </button>
        )}

        {status === 'failed' && onRetry && (
          <button
            onClick={onRetry}
            className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
          >
            重试
          </button>
        )}
      </div>

      {/* 进度条 */}
      {status === 'uploading' && (
        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className="bg-blue-500 h-2 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* 速度和剩余时间 */}
      {status === 'uploading' && (speed || estimatedTime) && (
        <div className="flex items-center justify-between text-xs text-gray-500">
          {speed && <span>速度: {formatSpeed(speed)}</span>}
          {estimatedTime && <span>剩余: {formatTime(estimatedTime)}</span>}
        </div>
      )}

      {/* 错误信息 */}
      {status === 'failed' && error && (
        <div className="flex items-start space-x-2 p-3 bg-red-50 rounded-md">
          <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* 成功状态 */}
      {status === 'ready' && (
        <div className="flex items-center space-x-2 text-sm text-green-600">
          <CheckCircle className="w-4 h-4" />
          <span>上传成功</span>
        </div>
      )}
    </div>
  );
}
