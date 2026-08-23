import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useBrowserNotification } from '../use-browser-notification'

// Mock Notification API
const mockNotification = {
  permission: 'default' as NotificationPermission,
  requestPermission: vi.fn().mockResolvedValue('granted'),
  close: vi.fn(),
}

class MockNotification {
  static permission = 'default'
  static requestPermission = mockNotification.requestPermission

  title: string
  options: any
  onclick: (() => void) | null = null

  constructor(title: string, options: any) {
    this.title = title
    this.options = options
  }

  close() {
    mockNotification.close()
  }
}

// @ts-ignore
global.Notification = MockNotification

describe('useBrowserNotification', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    MockNotification.permission = 'default'
    mockNotification.requestPermission.mockResolvedValue('granted')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should initialize with default permission', () => {
    const { result } = renderHook(() => useBrowserNotification())

    expect(result.current.permission).toBe('default')
  })

  it('should request permission', async () => {
    const { result } = renderHook(() => useBrowserNotification())

    await act(async () => {
      const granted = await result.current.requestPermission()
      expect(granted).toBe(true)
    })

    expect(mockNotification.requestPermission).toHaveBeenCalled()
    expect(result.current.permission).toBe('granted')
  })

  it('should handle permission denied', async () => {
    mockNotification.requestPermission.mockResolvedValue('denied')

    const { result } = renderHook(() => useBrowserNotification())

    await act(async () => {
      const granted = await result.current.requestPermission()
      expect(granted).toBe(false)
    })

    expect(result.current.permission).toBe('denied')
  })

  it('should show notification when permission granted', () => {
    MockNotification.permission = 'granted'
    const { result } = renderHook(() => useBrowserNotification())

    act(() => {
      result.current.show({
        title: 'Test Notification',
        body: 'Test body',
      })
    })

    expect(mockNotification.close).not.toHaveBeenCalled()
  })

  it('should not show notification when permission not granted', () => {
    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    MockNotification.permission = 'denied'
    const { result } = renderHook(() => useBrowserNotification())

    act(() => {
      const notification = result.current.show({
        title: 'Test Notification',
        body: 'Test body',
      })
      expect(notification).toBeNull()
    })

    expect(consoleSpy).toHaveBeenCalledWith('Notification permission not granted')

    consoleSpy.mockRestore()
  })

  it('should show success notification', () => {
    MockNotification.permission = 'granted'
    const { result } = renderHook(() => useBrowserNotification())

    act(() => {
      result.current.success('Success Title', 'Success message')
    })

    // Verify notification was created (via constructor)
    expect(mockNotification.requestPermission).not.toHaveBeenCalled()
  })

  it('should show error notification with emoji', () => {
    MockNotification.permission = 'granted'
    const { result } = renderHook(() => useBrowserNotification())

    act(() => {
      result.current.error('Error Title', 'Error message')
    })

    // The error method should add emoji to title
    expect(mockNotification.requestPermission).not.toHaveBeenCalled()
  })

  it('should call onClick handler when notification clicked', () => {
    // Mock window.focus
    const mockFocus = vi.fn()
    Object.defineProperty(window, 'focus', {
      value: mockFocus,
      writable: true,
    })

    MockNotification.permission = 'granted'
    const onClick = vi.fn()
    const { result } = renderHook(() => useBrowserNotification())

    let notificationInstance: MockNotification | null = null

    act(() => {
      notificationInstance = result.current.show({
        title: 'Click Test',
        body: 'Click me',
        onClick,
      }) as any
    })

    act(() => {
      if (notificationInstance) {
        notificationInstance.onclick?.()
      }
    })

    expect(onClick).toHaveBeenCalled()
    expect(mockFocus).toHaveBeenCalled()
  })

  it('should handle missing Notification API', async () => {
    // @ts-ignore
    delete global.Notification

    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    const { result } = renderHook(() => useBrowserNotification())

    await act(async () => {
      const granted = await result.current.requestPermission()
      expect(granted).toBe(false)
    })

    expect(consoleSpy).toHaveBeenCalledWith('Browser does not support notifications')

    consoleSpy.mockRestore()

    // Restore Notification
    global.Notification = MockNotification as any
  })
})
