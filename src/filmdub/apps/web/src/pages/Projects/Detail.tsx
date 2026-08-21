import { Card, Descriptions, Button, Space, Divider, Table, Tag, Progress, Typography, Tabs } from 'antd'
import { ArrowLeftOutlined, PlayCircleOutlined, PauseCircleOutlined, StopOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'

const { Title, Text } = Typography
const { TabPane } = Tabs

function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const jobColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: '模块',
      dataIndex: 'module',
      key: 'module',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = {
          pending: 'default',
          running: 'processing',
          completed: 'success',
          failed: 'error',
        }
        return <Tag color={colors[status]}>{status}</Tag>
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number) => <Progress percent={progress} size="small" />,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
    },
  ]

  const artifactColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
    },
  ]

  const mockJobs = [
    {
      key: '1',
      id: 'job_001',
      module: 'M01 - 媒体接入',
      status: 'completed',
      progress: 100,
      created_at: '2024-01-15 10:35:00',
    },
    {
      key: '2',
      id: 'job_002',
      module: 'M05 - 音频分析',
      status: 'running',
      progress: 65,
      created_at: '2024-01-15 10:40:00',
    },
    {
      key: '3',
      id: 'job_003',
      module: 'M09 - 语音合成',
      status: 'pending',
      progress: 0,
      created_at: '2024-01-15 10:45:00',
    },
  ]

  const mockArtifacts = [
    {
      key: '1',
      id: 'art_001',
      type: 'video',
      name: '原始视频.mp4',
      size: '1.2 GB',
      created_at: '2024-01-15 10:35:00',
    },
    {
      key: '2',
      id: 'art_002',
      type: 'audio',
      name: '提取音频.wav',
      size: '45 MB',
      created_at: '2024-01-15 10:40:00',
    },
  ]

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
          <Descriptions.Item label="优先级">高 (3)</Descriptions.Item>
          <Descriptions.Item label="进度">
            <Progress percent={65} />
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">2024-01-15 10:30:00</Descriptions.Item>
          <Descriptions.Item label="更新时间">2024-01-16 14:20:00</Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>
            示例电影项目，用于演示 AI 配音功能
          </Descriptions.Item>
        </Descriptions>

        <Divider />

        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlayCircleOutlined />}>
            继续处理
          </Button>
          <Button icon={<PauseCircleOutlined />}>暂停</Button>
          <Button danger icon={<StopOutlined />}>取消</Button>
        </Space>
      </Card>

      <Card style={{ marginTop: 24 }}>
        <Tabs defaultActiveKey="jobs">
          <TabPane tab="作业列表" key="jobs">
            <Table
              columns={jobColumns}
              dataSource={mockJobs}
              pagination={false}
            />
          </TabPane>
          <TabPane tab="Artifacts" key="artifacts">
            <Table
              columns={artifactColumns}
              dataSource={mockArtifacts}
              pagination={false}
            />
          </TabPane>
          <TabPane tab="日志" key="logs">
            <Text type="secondary">日志将在这里显示...</Text>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

export default ProjectDetail
