import { Button, Table, Tag, Typography, Space } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title } = Typography

function Projects() {
  const navigate = useNavigate()

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: '项目名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = {
          created: 'default',
          processing: 'processing',
          completed: 'success',
          failed: 'error',
        }
        return <Tag color={colors[status]}>{status}</Tag>
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: any) => (
        <Space>
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/projects/${record.id}`)}
          />
          <Button type="text" icon={<EditOutlined />} />
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Space>
      ),
    },
  ]

  const mockData = [
    {
      key: '1',
      id: 'proj_001',
      name: '电影示例项目',
      status: 'completed',
      created_at: '2024-01-15',
    },
    {
      key: '2',
      id: 'proj_002',
      name: '电视剧集配音',
      status: 'processing',
      created_at: '2024-01-16',
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2}>Projects</Title>
        <Button type="primary" icon={<PlusOutlined />}>
          新建项目
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={mockData}
        pagination={{ pageSize: 10 }}
      />
    </div>
  )
}

export default Projects
