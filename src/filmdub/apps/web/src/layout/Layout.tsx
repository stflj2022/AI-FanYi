import React from 'react'
import Header from './Header'
import Sidebar from './Sidebar'
import { Outlet } from 'react-router-dom'
import { useUIStore } from '@/store'

const Layout: React.FC = () => {
  const { sidebarCollapsed } = useUIStore()

  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar />

      <div
        className={`flex-1 flex flex-col transition-all duration-300 ${
          sidebarCollapsed ? 'ml-16' : 'ml-64'
        }`}
      >
        <Header />

        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default Layout
