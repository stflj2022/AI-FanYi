import { Card, Row, Col, Statistic, Typography } from 'antd'
import { ProjectOutlined, CheckCircleOutlined, ClockCircleOutlined, AlertOutlined } from '@ant-design/icons'

const { Title } = Typography

function Dashboard() {
  return (
    <div>
      <Title level={2}>Dashboard</Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总项目数"
              value={12}
              prefix={<ProjectOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已完成"
              value={8}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="进行中"
              value={3}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败"
              value={1}
              prefix={<AlertOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="最近项目" style={{ marginBottom: 24 }}>
        <p>项目列表将在这里显示...</p>
      </Card>
    </div>
  )
}

export default Dashboard
