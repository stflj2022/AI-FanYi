import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Layout from '@/layout/Layout'
import Dashboard from '@/components/Dashboard'
import Projects from '@/components/Projects'
import Workers from '@/components/Workers'
import Settings from '@/components/Settings'

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
        element: <Projects />,
      },
      {
        path: 'projects/:id',
        element: <Projects />,
      },
      {
        path: 'workers',
        element: <Workers />,
      },
      {
        path: 'settings',
        element: <Settings />,
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
