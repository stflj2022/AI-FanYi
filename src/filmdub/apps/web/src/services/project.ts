import { apiClient } from './api'

export interface Project {
  id: string
  name: string
  description: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  priority: number
  created_at: string
  updated_at: string
  workflow_id?: string
}

export interface CreateProjectRequest {
  name: string
  description: string
  priority?: number
}

export interface UpdateProjectRequest {
  name?: string
  description?: string
  status?: string
  priority?: number
}

export interface Job {
  id: string
  project_id: string
  module_id: string
  status: string
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface Artifact {
  id: string
  project_id: string
  type: string
  uri: string
  size: number
  created_at: string
}

export const projectService = {
  // 获取项目列表
  listProjects: async (params?: {
    page?: number
    page_size?: number
    status?: string
  }) => {
    return apiClient.get('/projects', { params })
  },

  // 获取项目详情
  getProject: async (id: string) => {
    return apiClient.get(`/projects/${id}`)
  },

  // 创建项目
  createProject: async (data: CreateProjectRequest) => {
    return apiClient.post('/projects', data)
  },

  // 更新项目
  updateProject: async (id: string, data: UpdateProjectRequest) => {
    return apiClient.put(`/projects/${id}`, data)
  },

  // 删除项目
  deleteProject: async (id: string) => {
    return apiClient.delete(`/projects/${id}`)
  },

  // 获取项目作业
  listJobs: async (projectId: string) => {
    return apiClient.get(`/projects/${projectId}/jobs`)
  },

  // 获取项目 Artifacts
  listArtifacts: async (projectId: string) => {
    return apiClient.get(`/projects/${projectId}/artifacts`)
  },

  // 创建作业
  createJob: async (projectId: string, data: any) => {
    return apiClient.post(`/projects/${projectId}/jobs`, data)
  },

  // 上传文件
  uploadFile: async (file: File, onProgress?: (progress: number) => void) => {
    const formData = new FormData()
    formData.append('file', file)

    return apiClient.post('/artifacts/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          onProgress(progress)
        }
      },
    })
  },
}
