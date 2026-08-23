import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '../types'
import { authAPI } from '../services/authAPI'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // Actions
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string, confirmPassword: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: authAPI.getStoredUser(),
      isAuthenticated: authAPI.isAuthenticated(),
      isLoading: false,
      error: null,

      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await authAPI.login({ username, password })
          authAPI.saveTokens(response.access_token, response.refresh_token, response.user)
          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.response?.data?.detail || '登录失败，请检查用户名和密码',
          })
          throw error
        }
      },

      register: async (
        username: string,
        email: string,
        password: string,
        confirmPassword: string,
      ) => {
        set({ isLoading: true, error: null })
        try {
          await authAPI.register({
            username,
            email,
            password,
            confirm_password: confirmPassword,
          })
          set({ isLoading: false, error: null })
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.response?.data?.detail || '注册失败，请稍后重试',
          })
          throw error
        }
      },

      logout: async () => {
        try {
          await authAPI.logout()
        } finally {
          authAPI.clearTokens()
          set({
            user: null,
            isAuthenticated: false,
            error: null,
          })
        }
      },

      refreshUser: async () => {
        set({ isLoading: true, error: null })
        try {
          const user = await authAPI.getCurrentUser()
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
        } catch (error: any) {
          // 如果 Token 过期，尝试刷新
          const refreshToken = authAPI.getRefreshToken()
          if (refreshToken) {
            try {
              const response = await authAPI.refreshTokenSimple(refreshToken)
              authAPI.saveTokens(response.access_token, response.refresh_token, response.user)
              set({
                user: response.user,
                isAuthenticated: true,
                isLoading: false,
                error: null,
              })
              return
            } catch (refreshError) {
              // 刷新失败，清除认证状态
              authAPI.clearTokens()
              set({
                user: null,
                isAuthenticated: false,
                isLoading: false,
                error: null,
              })
              return
            }
          }
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          })
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
