import { useEffect, useState, useCallback, useRef } from 'react'
import { useWebSocket } from './use-websocket'
import { useAuthStore } from '../store/authStore'

export interface JobEvent {
  event_type: string
  job_id: string
  timestamp: string
  data: any
}

export interface JobProgressEvent extends JobEvent {
  event_type: 'job.progress'
  data: {
    job_id: string
    progress: number
    stage?: string
    message?: string
  }
}

export interface JobStageEvent extends JobEvent {
  event_type: 'job.stage'
  data: {
    job_id: string
    stage: string
    previous_stage?: string
    message?: string
  }
}

export interface JobCompletedEvent extends JobEvent {
  event_type: 'job.completed'
  data: {
    job_id: string
    status: string
    duration?: number
    output_artifacts?: string[]
  }
}

export interface JobFailedEvent extends JobEvent {
  event_type: 'job.failed'
  data: {
    job_id: string
    error_message: string
    error_stack?: string
    stage?: string
  }
}

export interface UseJobEventsOptions {
  onProgress?: (event: JobProgressEvent) => void
  onStage?: (event: JobStageEvent) => void
  onCompleted?: (event: JobCompletedEvent) => void
  onFailed?: (event: JobFailedEvent) => void
  onError?: (error: Event) => void
}

export function useJobEvents(jobId: string, options: UseJobEventsOptions = {}) {
  const { token } = useAuthStore()
  const [isSubscribed, setIsSubscribed] = useState(false)
  const wsRef = useRef<any>(null)

  // 构建 WebSocket URL
  const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8001'}/api/v1/ws/jobs?token=${token}`

  // WebSocket 消息处理
  const handleMessage = useCallback((message: JobEvent) => {
    console.log('[Job Events] Received event:', message)

    switch (message.event_type) {
      case 'job.progress':
        if (options.onProgress) {
          options.onProgress(message as JobProgressEvent)
        }
        break
      case 'job.stage':
        if (options.onStage) {
          options.onStage(message as JobStageEvent)
        }
        break
      case 'job.completed':
        if (options.onCompleted) {
          options.onCompleted(message as JobCompletedEvent)
        }
        break
      case 'job.failed':
        if (options.onFailed) {
          options.onFailed(message as JobFailedEvent)
        }
        break
      default:
        console.log('[Job Events] Unhandled event type:', message.event_type)
    }
  }, [options])

  // WebSocket 连接
  const { isConnected, send, disconnect, connect } = useWebSocket(wsUrl, {
    onMessage: handleMessage,
    onOpen: () => {
      console.log('[Job Events] WebSocket connected')
      // 连接成功后自动订阅
      subscribe()
    },
    onClose: () => {
      console.log('[Job Events] WebSocket disconnected')
      setIsSubscribed(false)
    },
    onError: options.onError,
  })

  // 订阅任务
  const subscribe = useCallback(() => {
    if (isConnected && jobId) {
      send({
        action: 'subscribe',
        job_id: jobId,
      })
      setIsSubscribed(true)
      console.log(`[Job Events] Subscribed to job ${jobId}`)
    }
  }, [isConnected, jobId, send])

  // 取消订阅
  const unsubscribe = useCallback(() => {
    if (isConnected && jobId) {
      send({
        action: 'unsubscribe',
        job_id: jobId,
      })
      setIsSubscribed(false)
      console.log(`[Job Events] Unsubscribed from job ${jobId}`)
    }
  }, [isConnected, jobId, send])

  // 当 jobId 变化时重新订阅
  useEffect(() => {
    if (isConnected && jobId) {
      // 先取消旧的订阅（如果有）
      if (isSubscribed) {
        unsubscribe()
      }
      // 订阅新的任务
      subscribe()
    }
  }, [jobId, isConnected, isSubscribed, subscribe, unsubscribe])

  // 清理
  useEffect(() => {
    return () => {
      if (isSubscribed) {
        unsubscribe()
      }
    }
  }, [isSubscribed, unsubscribe])

  return {
    isConnected,
    isSubscribed,
    subscribe,
    unsubscribe,
  }
}
