import { create } from 'zustand'

interface AppState {
  currentProjectId: string | null
  selectedJobIds: string[]
  sidebarCollapsed: boolean
  setCurrentProjectId: (id: string | null) => void
  toggleJobSelection: (id: string) => void
  clearJobSelection: () => void
  toggleSidebar: () => void
}

export const useAppStore = create<AppState>((set) => ({
  currentProjectId: null,
  selectedJobIds: [],
  sidebarCollapsed: false,

  setCurrentProjectId: (id) => set({ currentProjectId: id }),

  toggleJobSelection: (id) =>
    set((state) => ({
      selectedJobIds: state.selectedJobIds.includes(id)
        ? state.selectedJobIds.filter((x) => x !== id)
        : [...state.selectedJobIds, id],
    })),

  clearJobSelection: () => set({ selectedJobIds: [] }),

  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
}))
