import { create } from 'zustand'

interface Project {
  id: string
  name: string
  status: string
  created_at: string
  updated_at: string
}

interface ProjectState {
  projects: Project[]
  currentProject: Project | null
  loading: boolean
  setProjects: (projects: Project[]) => void
  setCurrentProject: (project: Project | null) => void
  setLoading: (loading: boolean) => void
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  currentProject: null,
  loading: false,
  setProjects: (projects) => set({ projects }),
  setCurrentProject: (project) => set({ currentProject: project }),
  setLoading: (loading) => set({ loading }),
}))
