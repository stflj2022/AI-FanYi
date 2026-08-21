import { useParams } from 'react-router-dom'
import { Typography, Card, Descriptions, Button, Space, Divider, Steps, Tag } from 'antd'
import { ArrowLeftOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title, Text } = Typography
const { Step } = Steps

function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const currentStep = 2

  return (
    <div>
      <Space style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/projects')}>
          返回
        </Button>
        <Title level={2} style={{ margin: 0 }}>
          项目详情
        </Title>
      </Space>

      <Card>
        <Descriptions title="项目信息" bordered column={2}>
          <Descriptions.Item label="项目 ID">{id}</Descriptions.Item>
          <Descriptions.Item label="项目名称">电影示例项目</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color="processing">处理中</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="优先级">高</Descriptions.Item>
          <Descriptions.Item label="创建时间">2024-01-15 10:30:00</Descriptions.Item>
          <Descriptions.Item label="更新时间">2024-01-16 14:20:00</Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>
            示例电影项目，用于演示 AI 配音功能
          </Descriptions.Item>
        </Descriptions>

        <Divider />

        <Title level={4}>处理进度</Title>
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          <Step title="媒体接入" description="M01" />
          <Step title="研究与分析" description="M02-M05" />
          <Step title="角色与映射" description="M06" />
          <Step title="对白处理" description="M07-M09" />
          <Step title="视频组装" description="M11" />
        </Steps>

        <Space>
          <Button type="primary" icon={<PlayCircleOutlined />}>
            继续处理
          </Button>
          <Button>暂停</Button>
          <Button danger>取消</Button>
        </Space>
      </Card>
    </div>
  )
}

export default ProjectDetail
