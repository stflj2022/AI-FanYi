import api from './api'

export interface Project {
  id: string
  name: string
  description?: string
  status: string
  priority: number
  created_at: string
  updated_at: string
}

export const projectAPI = {
  // 获取项目列表
  list: (params?: any) => api.get('/projects', { params }),

  // 获取项目详情
  get: (id: string) => api.get(`/projects/${id}`),

  // 创建项目
  create: (data: Partial<Project>) => api.post('/projects', data),

  // 更新项目
  update: (id: string, data: Partial<Project>) => api.put(`/projects/${id}`, data),

  // 删除项目
  delete: (id: string) => api.delete(`/projects/${id}`),

  // 获取项目的作业
  jobs: (id: string) => api.get(`/projects/${id}/jobs`),
}
