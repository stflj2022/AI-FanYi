import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { Dashboard } from './pages/Dashboard'
import { HealthCheck } from './pages/HealthCheck'

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
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="health" element={<HealthCheck />} />
            <Route path="projects" element={<div>Projects Page (TODO)</div>} />
            <Route path="jobs" element={<div>Jobs Page (TODO)</div>} />
            <Route path="characters" element={<div>Characters Page (TODO)</div>} />
            <Route path="settings" element={<div>Settings Page (TODO)</div>} />
            <Route path="system" element={<div>System Status Page (TODO)</div>} />
          </Route>
          <Route path="/login" element={<div>Login Page (TODO)</div>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}

export default App
