import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useJobEvents } from '../use-job-events'
import { useAuthStore } from '../../store/auth'

// Mock WebSocket
class MockWebSocket {
  readyState: number = WebSocket.CONNECTING
  onopen: (() => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onclose: (() => void) | null = null

  static instances: MockWebSocket[] = []

  constructor(url: string) {
    MockWebSocket.instances.push(this)
    setTimeout(() => {
      this.readyState = WebSocket.OPEN
      this.onopen?.()
    }, 0)
  }

  send(data: string) {
    // Simulate ping-pong
    const message = JSON.parse(data)
    if (message.type === 'ping') {
      setTimeout(() => {
        this.onmessage?.(new MessageEvent('message', {
          data: JSON.stringify({ type: 'pong', timestamp: message.timestamp }),
        }))
      }, 0)
    }
  }

  close() {
    this.readyState = WebSocket.CLOSED
    this.onclose?.()
  }

  static reset() {
    MockWebSocket.instances = []
  }
}

// Mock WebSocket global
global.WebSocket = MockWebSocket as any

// Mock auth store
vi.mock('../../store/auth', () => ({
  useAuthStore: vi.fn(),
}))

describe('useJobEvents', () => {
  const mockToken = 'test-token-123'
  const mockJobId = '123e4567-e89b-12d3-a456-426614174000'

  beforeEach(() => {
    MockWebSocket.reset()
    vi.useFakeTimers()
    vi.mocked(useAuthStore).mockReturnValue({
      token: mockToken,
      user: null,
      isAuthenticated: true,
      setToken: vi.fn(),
      setUser: vi.fn(),
      logout: vi.fn(),
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  it('should establish WebSocket connection on mount', () => {
    renderHook(() => useJobEvents(mockJobId))

    expect(MockWebSocket.instances.length).toBe(1)
    const ws = MockWebSocket.instances[0]
    expect(ws).toBeInstanceOf(MockWebSocket)
  })

  it('should subscribe to job on connection', async () => {
    const onProgress = vi.fn()

    renderHook(() => useJobEvents(mockJobId, { onProgress }))

    const ws = MockWebSocket.instances[0]

    // Wait for connection and subscription
    await waitFor(() => {
      expect(ws.readyState).toBe(WebSocket.OPEN)
    })

    // Check subscription message
    const sentMessages: any[] = []
    const originalSend = ws.send.bind(ws)
    ws.send = (data: string) => {
      sentMessages.push(JSON.parse(data))
      return originalSend(data)
    }

    await waitFor(() => {
      expect(sentMessages.some((m) => m.action === 'subscribe' && m.job_id === mockJobId)).toBe(true)
    })
  })

  it('should handle job progress events', async () => {
    const onProgress = vi.fn()
    const { result } = renderHook(() => useJobEvents(mockJobId, { onProgress }))

    const ws = MockWebSocket.instances[0]

    // Wait for connection
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    // Simulate progress event
    const progressEvent = {
      event_type: 'job.progress',
      job_id: mockJobId,
      timestamp: new Date().toISOString(),
      data: {
        job_id: mockJobId,
        progress: 50,
        stage: 'processing',
        message: 'Processing video...',
      },
    }

    act(() => {
      ws.onmessage?.(new MessageEvent('message', { data: JSON.stringify(progressEvent) }))
    })

    expect(onProgress).toHaveBeenCalledWith(progressEvent)
  })

  it('should handle job stage events', async () => {
    const onStage = vi.fn()
    const { result } = renderHook(() => useJobEvents(mockJobId, { onStage }))

    const ws = MockWebSocket.instances[0]

    // Wait for connection
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    // Simulate stage event
    const stageEvent = {
      event_type: 'job.stage',
      job_id: mockJobId,
      timestamp: new Date().toISOString(),
      data: {
        job_id: mockJobId,
        stage: 'encoding',
        previous_stage: 'processing',
        message: 'Starting encoding...',
      },
    }

    act(() => {
      ws.onmessage?.(new MessageEvent('message', { data: JSON.stringify(stageEvent) }))
    })

    expect(onStage).toHaveBeenCalledWith(stageEvent)
  })

  it('should handle job completed events', async () => {
    const onCompleted = vi.fn()
    const { result } = renderHook(() => useJobEvents(mockJobId, { onCompleted }))

    const ws = MockWebSocket.instances[0]

    // Wait for connection
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    // Simulate completed event
    const completedEvent = {
      event_type: 'job.completed',
      job_id: mockJobId,
      timestamp: new Date().toISOString(),
      data: {
        job_id: mockJobId,
        status: 'completed',
        duration: 120.5,
        output_artifacts: ['output.mp4'],
      },
    }

    act(() => {
      ws.onmessage?.(new MessageEvent('message', { data: JSON.stringify(completedEvent) }))
    })

    expect(onCompleted).toHaveBeenCalledWith(completedEvent)
  })

  it('should handle job failed events', async () => {
    const onFailed = vi.fn()
    const { result } = renderHook(() => useJobEvents(mockJobId, { onFailed }))

    const ws = MockWebSocket.instances[0]

    // Wait for connection
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    // Simulate failed event
    const failedEvent = {
      event_type: 'job.failed',
      job_id: mockJobId,
      timestamp: new Date().toISOString(),
      data: {
        job_id: mockJobId,
        error_message: 'Processing failed',
        error_stack: 'Traceback...',
        stage: 'encoding',
      },
    }

    act(() => {
      ws.onmessage?.(new MessageEvent('message', { data: JSON.stringify(failedEvent) }))
    })

    expect(onFailed).toHaveBeenCalledWith(failedEvent)
  })

  it('should unsubscribe when jobId changes', async () => {
    const { result, rerender } = renderHook(
      ({ jobId }) => useJobEvents(jobId),
      { initialProps: { jobId: mockJobId } }
    )

    const ws = MockWebSocket.instances[0]

    // Wait for connection and subscription
    await waitFor(() => {
      expect(result.current.isSubscribed).toBe(true)
    })

    // Change job ID
    const newJobId = '223e4567-e89b-12d3-a456-426614174001'
    rerender({ jobId: newJobId })

    // Wait for re-subscription
    await waitFor(() => {
      expect(result.current.isSubscribed).toBe(true)
    })
  })

  it('should unsubscribe on unmount', async () => {
    const { result, unmount } = renderHook(() => useJobEvents(mockJobId))

    const ws = MockWebSocket.instances[0]

    // Wait for connection and subscription
    await waitFor(() => {
      expect(result.current.isSubscribed).toBe(true)
    })

    // Collect sent messages
    const sentMessages: any[] = []
    const originalSend = ws.send.bind(ws)
    ws.send = (data: string) => {
      sentMessages.push(JSON.parse(data))
      return originalSend(data)
    }

    unmount()

    // Check for unsubscribe message
    await waitFor(() => {
      expect(sentMessages.some((m) => m.action === 'unsubscribe' && m.job_id === mockJobId)).toBe(true)
    })
  })
})
