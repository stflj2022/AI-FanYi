import { io, Socket } from 'socket.io-client'
import { message } from 'antd'

class WebSocketService {
  private socket: Socket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 3000

  connect(url: string = '/ws', token?: string): Promise<Socket> {
    return new Promise((resolve, reject) => {
      try {
        this.socket = io(url, {
          auth: { token },
          reconnection: true,
          reconnectionDelay: this.reconnectDelay,
          reconnectionAttempts: this.maxReconnectAttempts,
        })

        this.socket.on('connect', () => {
          console.log('WebSocket connected:', this.socket?.id)
          this.reconnectAttempts = 0
          resolve(this.socket!)
        })

        this.socket.on('connect_error', (error) => {
          console.error('WebSocket connection error:', error)
          this.reconnectAttempts++

          if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            message.error('WebSocket 连接失败，请刷新页面重试')
            reject(error)
          }
        })

        this.socket.on('disconnect', (reason) => {
          console.log('WebSocket disconnected:', reason)
        })

        this.socket.on('error', (error) => {
          console.error('WebSocket error:', error)
        })
      } catch (error) {
        reject(error)
      }
    })
  }

  setReconnectDelay(delayMs: number) {
    if (delayMs > 0) {
      this.reconnectDelay = delayMs
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  on(event: string, callback: (...args: any[]) => void) {
    this.socket?.on(event, callback)
  }

  off(event: string, callback?: (...args: any[]) => void) {
    if (callback) {
      this.socket?.off(event, callback)
    } else {
      this.socket?.off(event)
    }
  }

  emit(event: string, data?: any) {
    this.socket?.emit(event, data)
  }

  subscribe(channel: string) {
    this.emit('subscribe', { channel })
  }

  unsubscribe(channel: string) {
    this.emit('unsubscribe', { channel })
  }

  sendPing() {
    this.emit('ping', { timestamp: Date.now() })
  }

  isConnected(): boolean {
    return this.socket?.connected ?? false
  }
}

export default new WebSocketService()
