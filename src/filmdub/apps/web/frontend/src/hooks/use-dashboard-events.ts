import { useEffect, useState, useCallback } from 'react'
import { useWebSocket } from './use-websocket'
import { useAuthStore } from '../store/authStore'

export interface DashboardEvent {
  event_type: string
  timestamp: string
  data: any
}

export interface JobCreatedEvent extends DashboardEvent {
  event_type: 'job.created'
  data: {
    job_id: string
    job_name: string
    project_id: string
  }
}

export interface JobStatusChangedEvent extends DashboardEvent {
  event_type: 'job.status_changed'
  data: {
    job_id: string
    old_status: string
    new_status: string
  }
}

export interface UseDashboardEventsOptions {
  onJobCreated?: (event: JobCreatedEvent) => void
  onJobStatusChanged?: (event: JobStatusChangedEvent) => void
  onAnyEvent?: (event: DashboardEvent) => void
  onError?: (error: Event) => void
}

export function useDashboardEvents(options: UseDashboardEventsOptions = {}) {
  const { token } = useAuthStore()
  const [isSubscribed, setIsSubscribed] = useState(false)

  // 构建 WebSocket URL
  const wsUrl = `${import.meta.env.VITE_WS_URL || window.location.origin.replace(/^http/, 'ws')}/api/v1/ws/jobs?token=${token ?? ''}`

  // WebSocket 消息处理
  const handleMessage = useCallback((message: DashboardEvent) => {
    console.log('[Dashboard Events] Received event:', message)

    // 调用通用回调
    if (options.onAnyEvent) {
      options.onAnyEvent(message)
    }

    switch (message.event_type) {
      case 'job.created':
        if (options.onJobCreated) {
          options.onJobCreated(message as JobCreatedEvent)
        }
        break
      case 'job.status_changed':
        if (options.onJobStatusChanged) {
          options.onJobStatusChanged(message as JobStatusChangedEvent)
        }
        break
      default:
        console.log('[Dashboard Events] Unhandled event type:', message.event_type)
    }
  }, [options])

  // WebSocket 连接
  const { isConnected, disconnect, connect } = useWebSocket(wsUrl, {
    onMessage: handleMessage,
    onOpen: () => {
      console.log('[Dashboard Events] WebSocket connected')
      setIsSubscribed(true)
    },
    onClose: () => {
      console.log('[Dashboard Events] WebSocket disconnected')
      setIsSubscribed(false)
    },
    onError: options.onError,
  })

  return {
    isConnected,
    isSubscribed,
  }
}
