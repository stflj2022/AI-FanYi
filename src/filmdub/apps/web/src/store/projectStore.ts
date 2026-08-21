import { create } from 'zustand'

export interface Project {
  id: string
  name: string
  description: string
  status: string
  priority: number
  created_at: string
  updated_at: string
}

export interface ProjectState {
  projects: Project[]
  currentProject: Project | null
  loading: boolean
  error: string | null

  fetchProjects: () => Promise<void>
  fetchProject: (id: string) => Promise<void>
  setCurrentProject: (project: Project | null) => void
  createProject: (data: any) => Promise<void>
  updateProject: (id: string, data: any) => Promise<void>
  deleteProject: (id: string) => Promise<void>
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  currentProject: null,
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null })
    try {
      const api = (await import('@/services/api')).default
      const response = await api.get('/projects')
      set({ projects: response.data || [], loading: false })
    } catch (error: any) {
      set({ error: error.message, loading: false })
    }
  },

  fetchProject: async (id: string) => {
    set({ loading: true, error: null })
    try {
      const api = (await import('@/services/api')).default
      const response = await api.get(`/projects/${id}`)
      set({ currentProject: response.data, loading: false })
    } catch (error: any) {
      set({ error: error.message, loading: false })
    }
  },

  setCurrentProject: (project) => {
    set({ currentProject: project })
  },

  createProject: async (data) => {
    set({ loading: true, error: null })
    try {
      const api = (await import('@/services/api')).default
      const response = await api.post('/projects', data)
      const newProject = response.data
      set((state) => ({
        projects: [...state.projects, newProject],
        loading: false
      }))
    } catch (error: any) {
      set({ error: error.message, loading: false })
    }
  },

  updateProject: async (id, data) => {
    set({ loading: true, error: null })
    try {
      const api = (await import('@/services/api')).default
      const response = await api.put(`/projects/${id}`, data)
      const updatedProject = response.data
      set((state) => ({
        projects: state.projects.map((p) =>
          p.id === id ? updatedProject : p
        ),
        currentProject:
          state.currentProject?.id === id ? updatedProject : state.currentProject,
        loading: false
      }))
    } catch (error: any) {
      set({ error: error.message, loading: false })
    }
  },

  deleteProject: async (id) => {
    set({ loading: true, error: null })
    try {
      const api = (await import('@/services/api')).default
      await api.delete(`/projects/${id}`)
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== id),
        currentProject:
          state.currentProject?.id === id ? null : state.currentProject,
        loading: false
      }))
    } catch (error: any) {
      set({ error: error.message, loading: false })
    }
  },
}))
