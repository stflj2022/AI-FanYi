import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../../store/auth'

interface PrivateRouteProps {
  children: React.ReactNode
  requireAdmin?: boolean
}

export function PrivateRoute({ children, requireAdmin = false }: PrivateRouteProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const user = useAuthStore((state) => state.user)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (requireAdmin && !user?.is_admin) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
