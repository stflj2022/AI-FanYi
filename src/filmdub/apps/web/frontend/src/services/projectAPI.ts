import { api } from './api'
import type { Project } from '../types'

/** 项目请求类型 */
export interface ProjectCreate {
  name: string
  description?: string
  title?: string
  title_en?: string
  season?: number
  episode?: number
  year?: number
  original_language?: string
  target_language: string
  media_type?: string
  tmdb_id?: number
  imdb_id?: string
  config?: Record<string, any>
}

export interface ProjectUpdate {
  name?: string
  description?: string
  title?: string
  title_en?: string
  season?: number
  episode?: number
  year?: number
  original_language?: string
  target_language?: string
  media_type?: string
  tmdb_id?: number
  imdb_id?: string
  config?: Record<string, any>
  status?: string
}

export interface ProjectListParams {
  page?: number
  page_size?: number
  search?: string
  status?: string
}

export interface ProjectListResponse {
  total: number
  page: number
  page_size: number
  items: Project[]
}

/** 项目 API */
export const projectAPI = {
  /** 创建项目 */
  create: async (data: ProjectCreate): Promise<Project> => {
    const response = await api.post<Project>('/projects', data)
    return response
  },

  /** 获取项目列表 */
  list: async (params: ProjectListParams = {}): Promise<ProjectListResponse> => {
    const response = await api.get<ProjectListResponse>('/projects', params)
    return response
  },

  /** 获取项目详情 */
  get: async (projectId: string): Promise<Project> => {
    const response = await api.get<Project>(`/projects/${projectId}`)
    return response
  },

  /** 更新项目 */
  update: async (projectId: string, data: ProjectUpdate): Promise<Project> => {
    const response = await api.put<Project>(`/projects/${projectId}`, data)
    return response
  },

  /** 删除项目 */
  delete: async (projectId: string): Promise<void> => {
    await api.delete(`/projects/${projectId}`)
  },
}
