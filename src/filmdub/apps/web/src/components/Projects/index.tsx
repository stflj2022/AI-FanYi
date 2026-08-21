import React, { useEffect, useState } from 'react'
import {
  Table,
  Button,
  Input,
  Select,
  Space,
  Tag,
  Modal,
  message,
  Upload,
  Form,
  Card,
  Tabs,
  Descriptions,
} from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  UploadOutlined,
  DownloadOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, useParams } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import { projectService, type Project, type Job, type Artifact } from '@/services/project'
import apiClient from '@/services/api'

const { Search } = Input
const { Option } = Select

const ProjectList: React.FC = () => {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 })
  const [createModalVisible, setCreateModalVisible] = useState(false)

  const [form] = Form.useForm()

  useEffect(() => {
    fetchProjects()
  }, [pagination.current, pagination.pageSize, statusFilter])

  const fetchProjects = async () => {
    setLoading(true)
    try {
      const response: any = await projectService.listProjects({
        page: pagination.current,
        page_size: pagination.pageSize,
        status: statusFilter,
      })
      setProjects(response.data || [])
      setPagination({
        ...pagination,
        total: response.total || 0,
      })
    } catch (error) {
      message.error('加载项目列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (value: string) => {
    setSearchText(value)
    // 客户端搜索
  }

  const handleStatusChange = (value: string) => {
    setStatusFilter(value)
    setPagination({ ...pagination, current: 1 })
  }

  const handleCreateProject = async (values: any) => {
    try {
      const created: any = await projectService.createProject(values)
      // 创建成功后若携带文件，上传到新项目（真实 Artifact 上传）
      if (values.files && values.files.length > 0 && created.data?.id) {
        const file = values.files[0]
        const formData = new FormData()
        formData.append('project_id', created.data.id)
        formData.append('file', file)
        formData.append('name', file.name)
        formData.append('artifact_type', 'video')
        try {
          await apiClient.post('/artifacts/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          })
          message.success('视频上传成功')
        } catch (uploadError) {
          message.warning('项目已创建，但视频上传失败')
        }
      }
      message.success('项目创建成功')
      setCreateModalVisible(false)
      form.resetFields()
      fetchProjects()
    } catch (error) {
      message.error('项目创建失败')
    }
  }

  const handleUpload = async (_file: File) => {
    // 项目列表中上传：提示先创建项目
    message.info('请先在项目中上传视频')
    return false
  }


  const statusColors: Record<string, string> = {
    pending: 'default',
    processing: 'processing',
    completed: 'success',
    failed: 'error',
  }

  const columns: ColumnsType<Project> = [
    {
      title: '项目名称',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <a onClick={() => navigate(`/projects/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={statusColors[status] || 'default'}>
          {status === 'pending' && '待处理'}
          {status === 'processing' && '处理中'}
          {status === 'completed' && '已完成'}
          {status === 'failed' && '失败'}
        </Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: number) => {
        const colors = ['red', 'orange', 'blue', 'green']
        const labels = ['高', '中高', '中', '低']
        return <Tag color={colors[priority - 1] || 'default'}>{labels[priority - 1] || '未知'}</Tag>
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => navigate(`/projects/${record.id}`)}
          >
            详情
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold">项目列表</h2>
        <Space>
          <Upload
            accept="video/*"
            showUploadList={false}
            beforeUpload={handleUpload}
          >
            <Button icon={<UploadOutlined />}>上传视频</Button>
          </Upload>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            创建项目
          </Button>
        </Space>
      </div>

      <Card className="mb-6">
        <Space size="large">
          <Search
            placeholder="搜索项目名称"
            allowClear
            onSearch={handleSearch}
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
          />
          <Select
            placeholder="筛选状态"
            allowClear
            style={{ width: 150 }}
            onChange={handleStatusChange}
          >
            <Option value="pending">待处理</Option>
            <Option value="processing">处理中</Option>
            <Option value="completed">已完成</Option>
            <Option value="failed">失败</Option>
          </Select>
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={projects.filter((p) =>
          p.name.toLowerCase().includes(searchText.toLowerCase())
        )}
        rowKey="id"
        loading={loading}
        pagination={{
          ...pagination,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, pageSize) =>
            setPagination({ ...pagination, current: page, pageSize: pageSize || 10 }),
        }}
      />

      <Modal
        title="创建项目"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateProject}>
          <Form.Item
            label="项目名称"
            name="name"
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input placeholder="请输入项目名称" />
          </Form.Item>
          <Form.Item
            label="项目描述"
            name="description"
            rules={[{ required: true, message: '请输入项目描述' }]}
          >
            <Input.TextArea rows={4} placeholder="请输入项目描述" />
          </Form.Item>
          <Form.Item label="优先级" name="priority" initialValue={3}>
            <Select>
              <Option value={1}>高</Option>
              <Option value={2}>中高</Option>
              <Option value={3}>中</Option>
              <Option value={4}>低</Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                创建
              </Button>
              <Button onClick={() => setCreateModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) {
      fetchProjectDetail()
    }
  }, [id])

  const fetchProjectDetail = async () => {
    setLoading(true)
    try {
      const [projectData, jobsData, artifactsData] = await Promise.all([
        projectService.getProject(id!),
        projectService.listJobs(id!),
        projectService.listArtifacts(id!),
      ])

      setProject((projectData as any).data || projectData)
      setJobs(jobsData.data || [])
      setArtifacts(artifactsData.data || [])
    } catch (error) {
      message.error('加载项目详情失败')
    } finally {
      setLoading(false)
    }
  }

  const jobColumns: ColumnsType<Job> = [
    { title: '模块', dataIndex: 'module_id', key: 'module_id' },
    { title: '状态', dataIndex: 'status', key: 'status' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
  ]

  const artifactColumns: ColumnsType<Artifact> = [
    { title: '类型', dataIndex: 'type', key: 'type' },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      render: (size: number) => `${(size / 1024 / 1024).toFixed(2)} MB`,
    },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<DownloadOutlined />}
          onClick={() => window.open(record.uri, '_blank')}
        >
          下载
        </Button>
      ),
    },
  ]

  if (loading) {
    return <div>加载中...</div>
  }

  return (
    <div>
      <Button className="mb-4" onClick={() => window.history.back()}>
        返回
      </Button>

      {project && (
        <>
          <Card className="mb-6">
            <Descriptions title={project.name} bordered column={2}>
              <Descriptions.Item label="描述" span={2}>
                {project.description}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={project.status === 'completed' ? 'success' : 'processing'}>
                  {project.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="优先级">{project.priority}</Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {new Date(project.created_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {new Date(project.updated_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Tabs defaultActiveKey="jobs">
            <Tabs.TabPane tab="作业" key="jobs">
              <Table
                columns={jobColumns}
                dataSource={jobs}
                rowKey="id"
                pagination={false}
              />
            </Tabs.TabPane>
            <Tabs.TabPane tab="文件" key="artifacts">
              <Table
                columns={artifactColumns}
                dataSource={artifacts}
                rowKey="id"
                pagination={false}
              />
            </Tabs.TabPane>
          </Tabs>
        </>
      )}
    </div>
  )
}

export default function Projects() {
  const location = useLocation()

  if (location.pathname.match(/\/projects\/\w+/)) {
    return <ProjectDetail />
  }

  return <ProjectList />
}
