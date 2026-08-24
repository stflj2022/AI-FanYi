import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useAppStore } from '../../store/app'
import { useAuthStore } from '../../store/authStore'
import { Button } from '../ui/button'
import { Home, FolderOpen, List, Users, Settings, Cpu, LogOut, User } from 'lucide-react'

export function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const sidebarCollapsed = useAppStore((state) => state.sidebarCollapsed)
  const toggleSidebar = useAppStore((state) => state.toggleSidebar)
  const { user, logout } = useAuthStore()

  const navigation = [
    { name: 'Dashboard', href: '/', icon: Home },
    { name: 'Projects', href: '/projects', icon: FolderOpen },
    { name: 'Jobs', href: '/jobs', icon: List },
    { name: 'Characters', href: '/characters', icon: Users },
    { name: 'Settings', href: '/settings', icon: Settings },
  ]

  const isActive = (path: string) => location.pathname === path

  return (
    <div className="flex h-screen bg-gray-50">
      {/* 侧边栏 */}
      <aside
        className={cn(
          'flex flex-col bg-white border-r border-gray-200 transition-all duration-300',
          sidebarCollapsed ? 'w-16' : 'w-64'
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-center h-16 border-b border-gray-200">
          {!sidebarCollapsed && (
            <h1 className="text-xl font-bold text-gray-800">AI 配音</h1>
          )}
          {sidebarCollapsed && <span className="text-2xl">🎬</span>}
        </div>

        {/* 导航菜单 */}
        <nav className="flex-1 px-2 py-4 space-y-1">
          {navigation.map((item) => (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                'flex items-center px-3 py-2 rounded-lg transition-colors',
                isActive(item.href)
                  ? 'bg-blue-50 text-blue-600'
                  : 'text-gray-700 hover:bg-gray-100'
              )}
            >
              <item.icon className={cn('flex-shrink-0', sidebarCollapsed ? 'mx-auto' : 'mr-3')} size={20} />
              {!sidebarCollapsed && <span>{item.name}</span>}
            </Link>
          ))}
        </nav>

        {/* 底部操作 */}
        <div className="p-2 border-t border-gray-200 space-y-1">
          <Link
            to="/system"
            className={cn(
              'flex items-center px-3 py-2 rounded-lg transition-colors',
              isActive('/system')
                ? 'bg-blue-50 text-blue-600'
                : 'text-gray-700 hover:bg-gray-100'
            )}
          >
            <Cpu className={cn('flex-shrink-0', sidebarCollapsed ? 'mx-auto' : 'mr-3')} size={20} />
            {!sidebarCollapsed && <span>System</span>}
          </Link>
          <button
            className="w-full flex items-center px-3 py-2 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
            onClick={async () => {
              await logout()
              navigate('/login')
            }}
          >
            <LogOut className={cn('flex-shrink-0', sidebarCollapsed ? 'mx-auto' : 'mr-3')} size={20} />
            {!sidebarCollapsed && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 顶部栏 */}
        <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleSidebar}
          >
            ☰
          </Button>
          <div className="flex items-center space-x-4">
            {user && (
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <User size={16} />
                <span>{user.username}</span>
                {user.is_admin && (
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                    Admin
                  </span>
                )}
              </div>
            )}
            <span className="text-sm text-gray-400">|</span>
            <span className="text-sm text-gray-600">Web UI v1.0.0</span>
          </div>
        </header>

        {/* 内容区域 */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function cn(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(' ')
}
