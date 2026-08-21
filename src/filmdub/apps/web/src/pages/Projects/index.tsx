import { Outlet } from 'react-router-dom'
import { Layout, Typography } from 'antd'

const { Content } = Layout
const { Title } = Typography

function Projects() {
  return (
    <Content style={{ padding: 24 }}>
      <Title level={2} style={{ marginBottom: 24 }}>
        Projects
      </Title>
      <Outlet />
    </Content>
  )
}

export default Projects
