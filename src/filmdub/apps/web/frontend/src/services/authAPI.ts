import { api } from './api'
import type { User } from '../types'

/** 认证相关接口类型 */
export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  confirm_password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

/** 认证 API 服务 */
export const authAPI = {
  /** 用户注册 */
  register: (data: RegisterRequest) =>
    api.postRaw<User>('/auth/register', data),

  /** 用户登录 */
  login: (data: LoginRequest) =>
    api.postRaw<TokenResponse>('/auth/login', data),

  /** 刷新 Token */
  refreshToken: (data: RefreshTokenRequest) =>
    api.postRaw<TokenResponse>('/auth/refresh', data),

  /** 刷新 Token（简化版本） */
  refreshTokenSimple: (refreshToken: string) =>
    api.postRaw<TokenResponse>('/auth/refresh', { refresh_token: refreshToken }),

  /** 用户登出 */
  logout: () =>
    api.postRaw<{ message: string }>('/auth/logout'),

  /** 获取当前用户信息 */
  getCurrentUser: () =>
    api.get<User>('/auth/me'),

  /** 修改密码 */
  changePassword: (data: ChangePasswordRequest) =>
    api.postRaw<{ message: string }>('/auth/change-password', data),

  /** 列出所有用户（管理员） */
  listUsers: () =>
    api.get<User[]>('/auth/users'),

  /** 检查是否已登录 */
  isAuthenticated: () => {
    return !!localStorage.getItem('access_token')
  },

  /** 获取存储的用户信息 */
  getStoredUser: (): User | null => {
    try {
      const userStr = localStorage.getItem('user')
      return userStr ? JSON.parse(userStr) : null
    } catch {
      return null
    }
  },

  /** 获取刷新 Token */
  getRefreshToken: (): string | null => {
    return localStorage.getItem('refresh_token')
  },

  /** 保存 Token */
  saveTokens: (accessToken: string, refreshToken: string, user: User) => {
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('refresh_token', refreshToken)
    localStorage.setItem('user', JSON.stringify(user))
  },

  /** 清除 Token */
  clearTokens: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
  },
}

export default authAPI
