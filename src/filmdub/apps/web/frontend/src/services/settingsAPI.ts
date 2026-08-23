import { api } from './api'

/** 用户设置类型 */
export interface UserSettings {
  id: string
  username: string
  email: string
  is_admin: boolean
  is_active: boolean
  settings: {
    default_target_language?: string
    default_video_quality?: string
    default_subtitle_format?: string
    auto_start_jobs?: boolean
    notification_enabled?: boolean
    theme?: string
  }
  created_at: string
  updated_at: string
}

/** 用户设置更新请求 */
export interface UserSettingsUpdate {
  username?: string
  email?: string
  default_target_language?: string
  default_video_quality?: string
  default_subtitle_format?: string
  auto_start_jobs?: boolean
  notification_enabled?: boolean
  theme?: string
}

/** 修改密码请求 */
export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

/** 设置 API */
export const settingsAPI = {
  /** 获取用户设置 */
  get: async (): Promise<UserSettings> => {
    const response = await api.get<UserSettings>('/settings')
    return response
  },

  /** 更新用户设置 */
  update: async (data: UserSettingsUpdate): Promise<UserSettings> => {
    const response = await api.put<UserSettings>('/settings', data)
    return response
  },

  /** 修改密码 */
  changePassword: async (data: ChangePasswordRequest): Promise<void> => {
    await api.post('/settings/change-password', data)
  },
}
