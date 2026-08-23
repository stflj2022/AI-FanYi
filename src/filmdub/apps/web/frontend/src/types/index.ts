/** API 基础类型 */

export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
}

/** 用户类型 */
export interface User {
  id: string
  username: string
  email: string
  is_admin: boolean
  is_active: boolean
  settings?: UserSettings
  created_at: string
  updated_at: string
}

/** 用户设置类型 */
export interface UserSettings {
  default_target_language?: string
  default_video_quality?: string
  default_subtitle_format?: string
  auto_start_jobs?: boolean
  notification_enabled?: boolean
  theme?: string
}

/** 项目类型 */
export interface Project {
  id: string
  name: string
  description?: string
  status: string
  title?: string
  title_en?: string
  season?: number
  episode?: number
  year?: number
  original_language?: string
  target_language: string
  owner_id?: string
  media_type?: string
  tmdb_id?: number
  imdb_id?: string
  config?: Record<string, any>
  created_at: string
  updated_at: string
  started_at?: string
  completed_at?: string
}

/** 任务类型 */
export interface Job {
  id: string
  project_id: string
  name: string
  status: string
  user_friendly_status?: string
  user_friendly_error?: string
  module_id?: string
  created_at: string
  updated_at: string
  started_at?: string
  completed_at?: string
  error_message?: string
}

/** 人物类型 */
export interface Character {
  id: string
  project_id: string
  name: string
  name_en?: string
  gender?: string
  age_range?: string
  role_type?: string
  actor_name?: string
  description?: string
  avatar_url?: string
  first_appearance_episode_name?: string
  created_at: string
  updated_at: string
}

/** 上传类型 */
export interface Upload {
  id: string
  filename: string
  file_size: number
  status: string
  progress?: number
  created_at: string
}

/** 系统状态类型 */
export interface SystemStatus {
  status: string
  cpu_usage: number
  memory_usage: number
  disk_usage: number
  workers: WorkerStatus[]
}

export interface WorkerStatus {
  id: string
  name: string
  status: string
  type: string
  jobs_completed: number
  jobs_failed: number
}
