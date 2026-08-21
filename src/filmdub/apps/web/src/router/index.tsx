import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Layout from '@/layout/Layout'
import Dashboard from '@/components/Dashboard'

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Dashboard />,
      },
      {
        path: 'projects',
        lazy: () => import('@/components/Projects'),
      },
      {
        path: 'projects/:id',
        lazy: () => import('@/components/ProjectDetail'),
      },
      {
        path: 'workers',
        lazy: () => import('@/components/Workers'),
      },
      {
        path: 'settings',
        lazy: () => import('@/components/Settings'),
      },
    ],
  },
  {
    path: '/login',
    element: <div>Login Page</div>,
  },
])

export default function Router() {
  return <RouterProvider router={router} />
}
