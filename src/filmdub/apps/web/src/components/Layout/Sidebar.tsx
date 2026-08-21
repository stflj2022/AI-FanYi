import { Layout, Menu } from 'antd'
import {
  DashboardOutlined,
  ProjectOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useLocation, useNavigate } from 'react-router-dom'
import { useUIStore } from '@/store'

const { Sider } = Layout

function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { sidebarCollapsed } = useUIStore()

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/projects',
      icon: <ProjectOutlined />,
      label: 'Projects',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    },
  ]

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  return (
    <Sider
      collapsible
      collapsed={sidebarCollapsed}
      trigger={null}
      style={{ overflow: 'auto', height: '100vh', position: 'fixed', left: 0, top: 0, bottom: 0 }}
    >
      <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#001529', color: '#fff' }}>
        <h2 style={{ color: '#fff', margin: 0 }}>AI-FanYi</h2>
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={handleMenuClick}
      />
    </Sider>
  )
}

export default Sidebar
