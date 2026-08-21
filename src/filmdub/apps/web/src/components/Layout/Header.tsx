import { Layout, Typography } from 'antd'
import { MenuUnfoldOutlined, MenuFoldOutlined } from '@ant-design/icons'
import { useUIStore } from '@/store'

const { Header: AntHeader } = Layout
const { Title } = Typography

function Header() {
  const { sidebarCollapsed, toggleSidebar } = useUIStore()

  return (
    <AntHeader style={{ padding: '0 24px', background: '#fff', display: 'flex', alignItems: 'center' }}>
      <div
        style={{ cursor: 'pointer', marginRight: 24 }}
        onClick={toggleSidebar}
      >
        {sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
      </div>
      <Title level={3} style={{ margin: 0 }}>AI-FanYi</Title>
    </AntHeader>
  )
}

export default Header
