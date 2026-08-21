import { Row, Col, Card, Typography, List, Tag, Space, Button } from 'antd'
import {
  ProjectOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  AlertOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import LineChartComponent from '@/components/Charts/LineChart'
import PieChartComponent from '@/components/Charts/PieChart'
import StatsCard from '@/components/StatsCard'

const { Title } = Typography

function Dashboard() {
  const projectTrendData = [
    { name: '周一', projects: 2 },
    { name: '周二', projects: 3 },
    { name: '周三', projects: 1 },
    { name: '周四', projects: 4 },
    { name: '周五', projects: 2 },
    { name: '周六', projects: 3 },
    { name: '周日', projects: 2 },
  ]

  const projectStatusData = [
    { name: '已完成', value: 8 },
    { name: '进行中', value: 3 },
    { name: '已创建', value: 1 },
  ]

  const recentActivities = [
    {
      id: 1,
      type: 'project_created',
      message: '创建了新项目 "动画配音测试"',
      time: '10分钟前',
    },
    {
      id: 2,
      type: 'job_completed',
      message: '作业 "M05 - 音频分析" 完成',
      time: '30分钟前',
    },
    {
      id: 3,
      type: 'project_completed',
      message: '项目 "电影示例项目" 完成',
      time: '2小时前',
    },
    {
      id: 4,
      type: 'job_failed',
      message: '作业 "M09 - 语音合成" 失败',
      time: '3小时前',
    },
  ]

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'project_created':
        return <ProjectOutlined style={{ color: '#1890ff' }} />
      case 'job_completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'project_completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'job_failed':
        return <AlertOutlined style={{ color: '#ff4d4f' }} />
      default:
        return <ClockCircleOutlined />
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          Dashboard
        </Title>
        <Button icon={<ReloadOutlined }}>刷新</Button>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <StatsCard
            title="总项目数"
            value={12}
            prefix={<ProjectOutlined />}
            valueStyle={{ color: '#1890ff' }}
          />
        </Col>
        <Col span={6}>
          <StatsCard
            title="已完成"
            value={8}
            prefix={<CheckCircleOutlined />}
            valueStyle={{ color: '#52c41a' }}
          />
        </Col>
        <Col span={6}>
          <StatsCard
            title="进行中"
            value={3}
            prefix={<ClockCircleOutlined />}
            valueStyle={{ color: '#faad14' }}
          />
        </Col>
        <Col span={6}>
          <StatsCard
            title="失败"
            value={1}
            prefix={<AlertOutlined />}
            valueStyle={{ color: '#ff4d4f' }}
          />
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        {/* 项目趋势图 */}
        <Col span={16}>
          <Card>
            <LineChartComponent
              data={projectTrendData}
              xKey="name"
              yKey="projects"
              title="项目创建趋势"
            />
          </Card>
        </Col>
        {/* 项目状态分布 */}
        <Col span={8}>
          <Card>
            <PieChartComponent
              data={projectStatusData}
              title="项目状态分布"
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        {/* 最近活动 */}
        <Col span={12}>
          <Card title="最近活动">
            <List
              dataSource={recentActivities}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={getActivityIcon(item.type)}
                    title={item.message}
                    description={item.time}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* Worker 状态 */}
        <Col span={12}>
          <Card title="Worker 状态">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Space>
                  <Tag color="success">运行中: 3</Tag>
                  <Tag>空闲: 2</Tag>
                  <Tag color="error">离线: 1</Tag>
                </Space>
              </div>
              <div style={{ marginTop: 16 }}>
                <Text type="secondary">Worker 负载分布将在这里显示...</Text>
              </div>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
