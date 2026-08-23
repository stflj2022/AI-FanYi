import { message } from 'antd'

type Listener = (...args: any[]) => void

/**
 * 原生 WebSocket 服务（与后端 filmdub.apps.api.websocket 的 JSON 文本协议对接）。
 * 保持与原先 socket.io 封装相同的对外 API：connect/on/off/emit/subscribe/
 * unsubscribe/sendPing/isConnected/disconnect/setReconnectDelay。
 *
 * 后端帧协议：文本 JSON，如
 *   服务端 -> {"type":"connected","connection_id":...}
 *   客户端 -> {"type":"subscribe","channel":...} / {"type":"ping","timestamp":...}
 */
class WebSocketService {
  private ws: WebSocket | null = null
  private url = ''
  private token?: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 3000
  private shouldReconnect = false
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private listeners: Record<string, Listener[]> = {}

  connect(url: string = '/ws', token?: string): Promise<WebSocket> {
    return new Promise((resolve, reject) => {
      try {
        this.url = url
        this.token = token

        // 把 /ws 之类的相对地址解析为带 locale 协议的完整 ws 地址
        if (!url.startsWith('ws')) {
          const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
          const base = window.location.host
          const path = url.startsWith('/') ? url : `/${url}`
          url = `${protocol}://${base}${path}`
        }

        const ws = new WebSocket(url)
        this.ws = ws
        this.shouldReconnect = true

        ws.onopen = () => {
          console.log('WebSocket connected')
          this.reconnectAttempts = 0
          this.notify('connect')
          resolve(ws)
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            // 同时派发到 'message'（useWebSocket 监听）和其 type 字段对应的事件
            this.notify('message', data)
            if (data && typeof data.type === 'string') {
              this.notify(data.type, data)
            }
          } catch {
            this.notify('message', event.data)
          }
        }

        ws.onclose = () => {
          this.notify('disconnect')
          if (this.shouldReconnect) {
            this.scheduleReconnect()
          }
        }

        ws.onerror = () => {
          this.reconnectAttempts++
          this.notify('error', new Error('WebSocket error'))
          if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            message.error('WebSocket 连接失败，请检查后端服务')
            reject(new Error('WebSocket connection failed'))
          }
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.connect(this.url, this.token).catch(() => {
          // 重连失败由 onerror 处理
        })
      }
    }, this.reconnectDelay)
  }

  setReconnectDelay(delayMs: number) {
    if (delayMs > 0) {
      this.reconnectDelay = delayMs
    }
  }

  disconnect() {
    this.shouldReconnect = false
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.listeners = {}
  }

  on(event: string, callback: Listener) {
    if (!this.listeners[event]) this.listeners[event] = []
    this.listeners[event].push(callback)
  }

  off(event: string, callback?: Listener) {
    if (!callback) {
      delete this.listeners[event]
      return
    }
    this.listeners[event] = (this.listeners[event] || []).filter((fn) => fn !== callback)
  }

  private notify(event: string, data?: any) {
    ;(this.listeners[event] || []).forEach((fn) => {
      try {
        fn(data)
      } catch (e) {
        console.error(e)
      }
    })
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(typeof data === 'string' ? data : JSON.stringify(data))
    }
  }

  // 发送业务消息（对接后端 handle_message 的类型协议）
  emit(event: string, data?: any) {
    this.send({ type: event, ...(data && typeof data === 'object' ? data : { data }) })
  }

  subscribe(channel: string) {
    this.send({ type: 'subscribe', channel })
  }

  unsubscribe(channel: string) {
    this.send({ type: 'unsubscribe', channel })
  }

  sendPing() {
    this.send({ type: 'ping', timestamp: Date.now() })
  }

  isConnected(): boolean {
    return !!this.ws && this.ws.readyState === WebSocket.OPEN
  }
}

export default new WebSocketService()
