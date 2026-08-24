import { useState, useEffect, useCallback } from 'react'
import { useWebSocket } from './use-websocket'

export interface JobProgress {
  job_id: string
  project_id: string
  progress: number
  status: string
  message: string
  timestamp: string
}

interface UseJobProgressOptions {
  jobId?: string
  projectId?: string
  token?: string
  onProgress?: (progress: JobProgress) => void
  onComplete?: () => void
  onError?: (error: string) => void
}

export function useJobProgress(options: UseJobProgressOptions = {}) {
  const { jobId, projectId, token, onProgress, onComplete, onError } = options

  const [progress, setProgress] = useState<JobProgress | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  // 构建 WebSocket URL
  const wsUrl = token
    ? `ws://localhost:8000/ws?token=${token}&project_id=${projectId || ''}`
    : `ws://localhost:8000/ws?project_id=${projectId || ''}`

  // 处理 WebSocket 消息
  const handleMessage = useCallback((message: any) => {
    // 处理作业进度消息
    if (message.type === 'job_progress' && message.job_id === jobId) {
      const progressData: JobProgress = {
        job_id: message.job_id,
        project_id: message.project_id,
        progress: message.progress,
        status: message.status,
        message: message.message,
        timestamp: message.timestamp,
      }

      setProgress(progressData)
      onProgress?.(progressData)

      // 完成检测
      if (progressData.status === 'completed' || progressData.progress >= 100) {
        onComplete?.()
      }
    }

    // 处理系统事件
    if (message.type === 'system_event') {
      console.log('System event:', message)
    }
  }, [jobId, onProgress, onComplete])

  // 使用 WebSocket
  const { isConnected: wsConnected, disconnect } = useWebSocket(wsUrl, {
    onMessage: handleMessage,
    onOpen: () => setIsConnected(true),
    onClose: () => setIsConnected(false),
  })

  // 重新连接
  const reconnect = useCallback(() => {
    disconnect()
    // 强制重新连接通过重新挂载组件实现
    window.location.reload()
  }, [disconnect])

  return {
    progress,
    isConnected: isConnected || wsConnected,
    reconnect,
  }
}

// 进度条组件 Props
export interface ProgressBarProps {
  progress?: JobProgress
  showStage?: boolean
  showDetails?: boolean
  className?: string
}

export function ProgressBar({
  progress,
  showStage = true,
  showDetails = true,
  className = '',
}: ProgressBarProps) {
  if (!progress) {
    return null
  }

  const { progress: value, message, status } = progress

  return (
    <div className={`job-progress ${className}`}>
      {/* 进度条 */}
      <div className="progress-bar-container">
        <div
          className="progress-bar-fill"
          style={{ width: `${value}%` }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>

      {/* 当前阶段 */}
      {showStage && (
        <div className="progress-stage">
          {message}
        </div>
      )}

      {/* 详细信息 */}
      {showDetails && (
        <div className="progress-details">
          <span className="progress-percent">{Math.round(value)}%</span>
          <span className="progress-status">
            {status === 'running' && '进行中'}
            {status === 'completed' && '已完成'}
            {status === 'failed' && '失败'}
          </span>
        </div>
      )}
    </div>
  )
}
