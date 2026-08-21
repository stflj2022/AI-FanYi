import { create } from 'zustand'

export interface UIState {
  sidebarCollapsed: boolean
  theme: 'light' | 'dark'
  loading: boolean

  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  setTheme: (theme: 'light' | 'dark') => void
  setLoading: (loading: boolean) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  theme: 'light',
  loading: false,

  toggleSidebar: () => {
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }))
  },

  setSidebarCollapsed: (collapsed) => {
    set({ sidebarCollapsed: collapsed })
  },

  setTheme: (theme) => {
    set({ theme })
    document.documentElement.setAttribute('data-theme', theme)
  },

  setLoading: (loading) => {
    set({ loading })
  },
}))
