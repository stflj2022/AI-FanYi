import { useEffect, useRef, useState, useCallback } from 'react'
import websocketService from '@/services/websocket'

export interface UseWebSocketOptions {
  autoConnect?: boolean
  token?: string
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: any) => void
  onMessage?: (message: any) => void
  reconnectInterval?: number
}

export interface WebSocketMessage {
  type: string
  data?: any
  timestamp?: string
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    autoConnect = true,
    token,
    onConnect,
    onDisconnect,
    onError,
    onMessage,
    reconnectInterval = 3000,
  } = options

  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [error, setError] = useState<any>(null)

  const callbacksRef = useRef({
    onConnect,
    onDisconnect,
    onError,
    onMessage,
  })

  // 更新回调引用
  useEffect(() => {
    callbacksRef.current = { onConnect, onDisconnect, onError, onMessage }
  }, [onConnect, onDisconnect, onError, onMessage])

  // 连接
  const connect = useCallback(async () => {
    try {
      websocketService.setReconnectDelay(reconnectInterval)
      await websocketService.connect('/ws', token)
      setIsConnected(true)
      setError(null)
      callbacksRef.current.onConnect?.()
    } catch (err) {
      setError(err)
      setIsConnected(false)
      callbacksRef.current.onError?.(err)
    }
  }, [token, reconnectInterval])

  // 断开连接
  const disconnect = useCallback(() => {
    websocketService.disconnect()
    setIsConnected(false)
    callbacksRef.current.onDisconnect?.()
  }, [])

  // 发送消息
  const sendMessage = useCallback((event: string, data?: any) => {
    websocketService.emit(event, data)
  }, [])

  // 订阅频道
  const subscribe = useCallback((channel: string) => {
    websocketService.subscribe(channel)
  }, [])

  // 取消订阅
  const unsubscribe = useCallback((channel: string) => {
    websocketService.unsubscribe(channel)
  }, [])

  // 自动连接
  useEffect(() => {
    if (autoConnect) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [autoConnect, connect, disconnect])

  // 监听消息
  useEffect(() => {
    const handleMessage = (message: WebSocketMessage) => {
      setLastMessage(message)
      callbacksRef.current.onMessage?.(message)
    }

    websocketService.on('message', handleMessage)

    return () => {
      websocketService.off('message', handleMessage)
    }
  }, [])

  return {
    isConnected,
    lastMessage,
    error,
    connect,
    disconnect,
    sendMessage,
    subscribe,
    unsubscribe,
  }
}
