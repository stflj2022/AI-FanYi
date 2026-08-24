import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { Dashboard } from './pages/Dashboard'
import { HealthCheck } from './pages/HealthCheck'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { ProjectList } from './pages/ProjectList'
import { ProjectCreate } from './pages/ProjectCreate'
import { ProjectDetail } from './pages/ProjectDetail'
import { Upload } from './pages/Upload'
import { JobList } from './pages/JobList'
import { Settings } from './pages/Settings'
import { SystemStatusPage } from './pages/SystemStatus'
import Characters from './pages/Characters'
import TranslationMemory from './pages/TranslationMemory'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="upload" element={<Upload />} />
            <Route path="health" element={<HealthCheck />} />
            <Route path="projects" element={<ProjectList />} />
            <Route path="projects/new" element={<ProjectCreate />} />
            <Route path="projects/:id" element={<ProjectDetail />} />
            <Route path="projects/:id/edit" element={<ProjectCreate />} />
            <Route path="jobs" element={<JobList />} />
            <Route path="characters" element={<Characters />} />
            <Route path="translation-memory" element={<TranslationMemory />} />
            <Route path="settings" element={<Settings />} />
            <Route path="system" element={<SystemStatusPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}

export default App
