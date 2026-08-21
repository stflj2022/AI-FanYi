import React from 'react'
import { Button, Layout as AntLayout } from 'antd'
import { MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons'
import { useUIStore } from '@/store'

const { Header: AntHeader } = AntLayout

const Header: React.FC = () => {
  const { sidebarCollapsed, toggleSidebar } = useUIStore()

  return (
    <AntHeader className="flex items-center justify-between bg-white px-6 shadow-sm">
      <div className="flex items-center gap-4">
        <Button
          type="text"
          icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={toggleSidebar}
          className="text-gray-600"
        />
        <h1 className="text-xl font-semibold text-gray-800">AI-FanYi</h1>
      </div>

      <div className="flex items-center gap-4">
        <Button type="text" className="text-gray-600">
          帮助
        </Button>
        <Button type="text" className="text-gray-600">
          用户
        </Button>
      </div>
    </AntHeader>
  )
}

export default Header
