import { Layout as AntLayout } from 'antd'
import { Outlet } from 'react-router-dom'
import Header from './Header'
import Sidebar from './Sidebar'

const { Content } = AntLayout

function Layout() {
  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sidebar />
      <AntLayout>
        <Header />
        <Content style={{ margin: '24px 16px', padding: 24, background: '#fff' }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}

export default Layout
