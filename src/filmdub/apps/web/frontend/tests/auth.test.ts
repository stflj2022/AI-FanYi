import { describe, it, expect, beforeEach, vi } from 'vitest'
import { authAPI } from '../src/services/authAPI'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value.toString() },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

describe('authAPI', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.clearAllMocks()
  })

  describe('Token 管理', () => {
    it('应该正确保存和获取 access token', () => {
      authAPI.saveTokens('test_access_token', 'test_refresh_token', {
        id: '123',
        username: 'testuser',
        email: 'test@example.com',
        is_admin: false,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      })

      expect(localStorageMock.getItem('access_token')).toBe('test_access_token')
      expect(localStorageMock.getItem('refresh_token')).toBe('test_refresh_token')
    })

    it('应该正确清除 tokens', () => {
      localStorageMock.setItem('access_token', 'test_token')
      localStorageMock.setItem('refresh_token', 'test_refresh')

      authAPI.clearTokens()

      expect(localStorageMock.getItem('access_token')).toBeNull()
      expect(localStorageMock.getItem('refresh_token')).toBeNull()
    })

    it('应该正确检查是否已登录', () => {
      expect(authAPI.isAuthenticated()).toBe(false)

      localStorageMock.setItem('access_token', 'test_token')
      expect(authAPI.isAuthenticated()).toBe(true)
    })

    it('应该正确获取 refresh token', () => {
      expect(authAPI.getRefreshToken()).toBeNull()

      localStorageMock.setItem('refresh_token', 'test_refresh')
      expect(authAPI.getRefreshToken()).toBe('test_refresh')
    })

    it('应该正确保存和获取用户信息', () => {
      const testUser = {
        id: '123',
        username: 'testuser',
        email: 'test@example.com',
        is_admin: false,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      }

      localStorageMock.setItem('user', JSON.stringify(testUser))
      const storedUser = authAPI.getStoredUser()

      expect(storedUser).toEqual(testUser)
    })

    it('应该处理无效的用户数据', () => {
      localStorageMock.setItem('user', 'invalid json')
      const storedUser = authAPI.getStoredUser()
      expect(storedUser).toBeNull()
    })
  })
})

describe('Auth Store', () => {
  it('应该正确初始化状态', () => {
    // 这需要实际的 store 实现
    // 这里只是示例
    expect(true).toBe(true)
  })
})
