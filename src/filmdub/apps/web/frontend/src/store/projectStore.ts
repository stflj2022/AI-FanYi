import { create } from 'zustand'
import type { Project, ProjectCreate, ProjectUpdate } from '../types'
import { projectAPI } from '../services/projectAPI'

interface ProjectListParams {
  page?: number
  page_size?: number
  search?: string
  status?: string
}

interface ProjectState {
  // 数据
  projects: Project[]
  currentProject: Project | null
  total: number
  page: number
  page_size: number

  // 状态
  isLoading: boolean
  isCreating: boolean
  isUpdating: boolean
  isDeleting: boolean
  error: string | null

  // Actions
  fetchProjects: (params?: ProjectListParams) => Promise<void>
  fetchProject: (projectId: string) => Promise<void>
  createProject: (data: ProjectCreate) => Promise<Project>
  updateProject: (projectId: string, data: ProjectUpdate) => Promise<void>
  deleteProject: (projectId: string) => Promise<void>
  clearCurrentProject: () => void
  clearError: () => void
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  // 初始状态
  projects: [],
  currentProject: null,
  total: 0,
  page: 1,
  page_size: 20,

  isLoading: false,
  isCreating: false,
  isUpdating: false,
  isDeleting: false,
  error: null,

  // 获取项目列表
  fetchProjects: async (params = {}) => {
    set({ isLoading: true, error: null })

    try {
      const response = await projectAPI.list({
        page: params.page || get().page,
        page_size: params.page_size || get().page_size,
        search: params.search,
        status: params.status,
      })

      set({
        projects: response.items,
        total: response.total,
        page: response.page,
        page_size: response.page_size,
        isLoading: false,
        error: null,
      })
    } catch (error: any) {
      set({
        isLoading: false,
        error: error.response?.data?.detail || '获取项目列表失败',
      })
      throw error
    }
  },

  // 获取项目详情
  fetchProject: async (projectId: string) => {
    set({ isLoading: true, error: null })

    try {
      const project = await projectAPI.get(projectId)
      set({
        currentProject: project,
        isLoading: false,
        error: null,
      })
    } catch (error: any) {
      set({
        isLoading: false,
        error: error.response?.data?.detail || '获取项目详情失败',
      })
      throw error
    }
  },

  // 创建项目
  createProject: async (data: ProjectCreate) => {
    set({ isCreating: true, error: null })

    try {
      const project = await projectAPI.create(data)
      set({
        isCreating: false,
        error: null,
        projects: [project, ...get().projects],
        total: get().total + 1,
      })
      return project
    } catch (error: any) {
      set({
        isCreating: false,
        error: error.response?.data?.detail || '创建项目失败',
      })
      throw error
    }
  },

  // 更新项目
  updateProject: async (projectId: string, data: ProjectUpdate) => {
    set({ isUpdating: true, error: null })

    try {
      const updatedProject = await projectAPI.update(projectId, data)

      set({
        isUpdating: false,
        error: null,
        currentProject: updatedProject,
        projects: get().projects.map((p) =>
          p.id === projectId ? updatedProject : p
        ),
      })
    } catch (error: any) {
      set({
        isUpdating: false,
        error: error.response?.data?.detail || '更新项目失败',
      })
      throw error
    }
  },

  // 删除项目
  deleteProject: async (projectId: string) => {
    set({ isDeleting: true, error: null })

    try {
      await projectAPI.delete(projectId)

      set({
        isDeleting: false,
        error: null,
        projects: get().projects.filter((p) => p.id !== projectId),
        total: get().total - 1,
        currentProject: get().currentProject?.id === projectId ? null : get().currentProject,
      })
    } catch (error: any) {
      set({
        isDeleting: false,
        error: error.response?.data?.detail || '删除项目失败',
      })
      throw error
    }
  },

  // 清除当前项目
  clearCurrentProject: () => set({ currentProject: null }),

  // 清除错误
  clearError: () => set({ error: null }),
}))
