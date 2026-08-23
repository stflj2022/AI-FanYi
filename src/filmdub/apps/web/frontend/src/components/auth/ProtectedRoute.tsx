import { useEffect } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, refreshUser, isLoading } = useAuthStore()
  const location = useLocation()

  useEffect(() => {
    // 如果有 token 但未标记为已认证，尝试刷新用户信息
    if (!isAuthenticated && !isLoading) {
      const token = localStorage.getItem('access_token')
      if (token) {
        refreshUser()
      }
    }
  }, [isAuthenticated, isLoading, refreshUser])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    // 保存当前路径，登录后跳转回来
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}
