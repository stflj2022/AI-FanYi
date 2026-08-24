/** 上传管理组件 - 管理多个上传任务 */
import { useState, useCallback } from 'react';
import { UploadArea } from './UploadArea';
import { UploadProgress } from './UploadProgress';
import { MediaInfo } from './MediaInfo';
import { X, ChevronDown, ChevronUp } from 'lucide-react';
import uploadAPI from '../../services/uploadAPI';
import type { UploadStatus, MediaType } from '../../services/uploadAPI';

interface UploadTask {
  id: string;
  file: File;
  progress: number;
  status: UploadStatus;
  speed?: number;
  estimatedTime?: number;
  error?: string;
  response?: any;
}

interface UploadManagerProps {
  projectId?: string;
  mediaType?: MediaType;
  onUploadComplete?: (taskId: string, response: any) => void;
  maxFiles?: number;
}

export function UploadManager({
  projectId,
  mediaType = 'video',
  onUploadComplete,
  maxFiles = 10,
}: UploadManagerProps) {
  const [tasks, setTasks] = useState<Map<string, UploadTask>>(new Map());
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());

  const handleUploadStart = useCallback((file: File) => {
    const taskId = crypto.randomUUID();
    const newTask: UploadTask = {
      id: taskId,
      file,
      progress: 0,
      status: 'uploading',
    };

    setTasks((prev) => {
      const updated = new Map(prev);
      if (updated.size >= maxFiles) {
        return prev; // 达到最大数量限制
      }
      updated.set(taskId, newTask);
      return updated;
    });

    return taskId;
  }, [maxFiles]);

  const handleUploadProgress = useCallback((taskId: string, progress: number) => {
    setTasks((prev) => {
      const updated = new Map(prev);
      const task = updated.get(taskId);
      if (task) {
        updated.set(taskId, {
          ...task,
          progress,
          status: 'uploading',
        });
      }
      return updated;
    });
  }, []);

  const handleUploadComplete = useCallback((taskId: string, response: any) => {
    setTasks((prev) => {
      const updated = new Map(prev);
      const task = updated.get(taskId);
      if (task) {
        updated.set(taskId, {
          ...task,
          progress: 100,
          status: 'ready',
          response,
        });
      }
      return updated;
    });

    onUploadComplete?.(taskId, response);
  }, [onUploadComplete]);

  const handleUploadError = useCallback((taskId: string, error: Error) => {
    setTasks((prev) => {
      const updated = new Map(prev);
      const task = updated.get(taskId);
      if (task) {
        updated.set(taskId, {
          ...task,
          status: 'failed',
          error: error.message,
        });
      }
      return updated;
    });
  }, []);

  const handleCancel = useCallback((taskId: string) => {
    setTasks((prev) => {
      const updated = new Map(prev);
      updated.delete(taskId);
      return updated;
    });
  }, []);

  const handleRetry = useCallback(async (taskId: string) => {
    const task = tasks.get(taskId);
    if (!task) return;

    // 重置任务状态
    setTasks((prev) => {
      const updated = new Map(prev);
      updated.set(taskId, {
        ...task,
        progress: 0,
        status: 'uploading',
        error: undefined,
      });
      return updated;
    });

    // 重新上传
    try {
      const response = await uploadAPI.uploadFile({
        file: task.file,
        project_id: projectId,
        media_type: mediaType,
        onProgress: (progress) => {
          handleUploadProgress(taskId, progress);
        },
      });
      handleUploadComplete(taskId, response);
    } catch (error) {
      handleUploadError(taskId, error as Error);
    }
  }, [tasks, projectId, mediaType, handleUploadProgress, handleUploadComplete, handleUploadError]);

  const handleRemove = useCallback((taskId: string) => {
    setTasks((prev) => {
      const updated = new Map(prev);
      updated.delete(taskId);
      return updated;
    });
    setExpandedTasks((prev) => {
      const updated = new Set(prev);
      updated.delete(taskId);
      return updated;
    });
  }, []);

  const toggleExpand = useCallback((taskId: string) => {
    setExpandedTasks((prev) => {
      const updated = new Set(prev);
      if (updated.has(taskId)) {
        updated.delete(taskId);
      } else {
        updated.add(taskId);
      }
      return updated;
    });
  }, []);

  const handleClearAll = useCallback(() => {
    setTasks(new Map());
    setExpandedTasks(new Set());
  }, []);

  const completedCount = Array.from(tasks.values()).filter((t) => t.status === 'ready').length;
  const failedCount = Array.from(tasks.values()).filter((t) => t.status === 'failed').length;
  const uploadingCount = Array.from(tasks.values()).filter((t) => t.status === 'uploading').length;

  return (
    <div className="space-y-4">
      {/* 上传区域 */}
      {tasks.size < maxFiles && (
        <UploadArea
          projectId={projectId}
          mediaType={mediaType}
          onUploadStart={handleUploadStart}
          onUploadProgress={handleUploadProgress}
          onUploadComplete={handleUploadComplete}
          onUploadError={handleUploadError}
        />
      )}

      {/* 统计信息 */}
      {tasks.size > 0 && (
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-4">
            <span className="text-gray-600">
              总计: {tasks.size} 个文件
            </span>
            {completedCount > 0 && (
              <span className="text-green-600">完成: {completedCount}</span>
            )}
            {failedCount > 0 && (
              <span className="text-red-600">失败: {failedCount}</span>
            )}
            {uploadingCount > 0 && (
              <span className="text-blue-600">上传中: {uploadingCount}</span>
            )}
          </div>
          <button
            onClick={handleClearAll}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            清空列表
          </button>
        </div>
      )}

      {/* 上传任务列表 */}
      <div className="space-y-3">
        {Array.from(tasks.values()).map((task) => (
          <div key={task.id} className="space-y-2">
            {/* 进度条 */}
            <UploadProgress
              filename={task.file.name}
              progress={task.progress}
              status={task.status}
              fileSize={task.file.size}
              speed={task.speed}
              estimatedTime={task.estimatedTime}
              error={task.error}
              onCancel={() => handleCancel(task.id)}
              onRetry={() => handleRetry(task.id)}
            />

            {/* 操作按钮和展开/收起 */}
            {task.status === 'ready' && (
              <div className="flex items-center justify-between">
                <button
                  onClick={() => toggleExpand(task.id)}
                  className="flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-800 transition-colors"
                >
                  <span>{expandedTasks.has(task.id) ? '收起' : '查看'}</span>
                  {expandedTasks.has(task.id) ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>

                <button
                  onClick={() => handleRemove(task.id)}
                  className="flex items-center space-x-1 text-sm text-gray-500 hover:text-gray-700 transition-colors"
                >
                  <X className="w-4 h-4" />
                  <span>移除</span>
                </button>
              </div>
            )}

            {/* 媒体信息 */}
            {task.status === 'ready' && expandedTasks.has(task.id) && task.response && (
              <div className="animate-in slide-in-from-top-2 duration-200">
                <MediaInfo metadata={task.response} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
