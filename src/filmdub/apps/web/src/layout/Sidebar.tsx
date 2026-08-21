import React from 'react'
import { Layout, Menu } from 'antd'
import {
  DashboardOutlined,
  ProjectOutlined,
  ClusterOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useUIStore } from '@/store'

const { Sider } = Layout

const Sidebar: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { sidebarCollapsed } = useUIStore()

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '仪表盘',
    },
    {
      key: '/projects',
      icon: <ProjectOutlined />,
      label: '项目',
    },
    {
      key: '/workers',
      icon: <ClusterOutlined />,
      label: 'Workers',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
  ]

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  return (
    <Sider
      collapsed={sidebarCollapsed}
      width={256}
      className="fixed left-0 top-0 h-screen bg-gray-900 text-white"
      theme="dark"
    >
      <div className="flex h-16 items-center justify-center border-b border-gray-700">
        <span className="text-xl font-bold">AI-FanYi</span>
      </div>

      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={handleMenuClick}
        className="mt-4"
      />
    </Sider>
  )
}

export default Sidebar
