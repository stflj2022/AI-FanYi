import { Table, Input, Select, Button, Space, Tag, Card, Progress, Typography } from 'antd'
import { PlusOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import { useState } from 'react'
import CreateProject from './Create'
import { useProjectStore } from '@/store'
import { projectAPI, Project } from '@/services/projectAPI'

const { Title } = Typography
const { Option } = Select

function ProjectsList() {
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [createVisible, setCreateVisible] = useState(false)
  const [loading, setLoading] = useState(false)

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 200,
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
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
    },
  ]

  const mockData: Project[] = [
    {
      id: 'proj_001',
      name: '电影示例项目',
      status: 'completed',
      priority: 3,
      created_at: '2024-01-15 10:30:00',
      updated_at: '2024-01-16 14:20:00',
    },
    {
      id: 'proj_002',
      name: '电视剧集配音',
      status: 'processing',
      priority: 2,
      created_at: '2024-01-16 09:00:00',
      updated_at: '2024-01-16 15:30:00',
    },
    {
      id: 'proj_003',
      name: '动画配音测试',
      status: 'created',
      priority: 1,
      created_at: '2024-01-17 11:00:00',
      updated_at: '2024-01-17 11:00:00',
    },
  ]

  const filteredData = mockData.filter((item) => {
    const matchesSearch = item.name.toLowerCase().includes(searchText.toLowerCase())
    const matchesStatus = statusFilter === 'all' || item.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const handleCreate = async (values: any) => {
    setLoading(true)
    try {
      await projectAPI.create(values)
      message.success('项目创建成功')
      setCreateVisible(false)
      // TODO: 重新加载项目列表
    } catch (error) {
      message.error('项目创建失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = () => {
    // TODO: 重新加载项目列表
    message.info('刷新成功')
  }

  return (
    <div>
      <Card>
        <Space style={{ marginBottom: 16 }} size="middle">
          <Input
            placeholder="搜索项目名称"
            prefix={<SearchOutlined />}
            style={{ width: 200 }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            style={{ width: 120 }}
          >
            <Option value="all">全部状态</Option>
            <Option value="created">已创建</Option>
            <Option value="processing">处理中</Option>
            <Option value="completed">已完成</Option>
            <Option value="failed">失败</Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateVisible(true)}>
            新建项目
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={filteredData}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>

      <CreateProject
        visible={createVisible}
        onCancel={() => setCreateVisible(false)}
        onCreate={handleCreate}
      />
    </div>
  )
}

export default ProjectsList
