import React, { useEffect, useState } from 'react'
import { Card, Table, Tag, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import apiClient from '@/services/api'

interface WorkerRow {
  id: string
  name: string
  status: string
  type: string
  cpu_cores: number
  memory_gb: number
  gpu_count: number
  jobs_completed: number
  jobs_failed: number
  last_heartbeat: string | null
}

const statusColors: Record<string, string> = {
  idle: 'green',
  busy: 'blue',
  starting: 'processing',
  stopping: 'warning',
  offline: 'default',
  error: 'red',
}

const Workers: React.FC = () => {
  const [workers, setWorkers] = useState<WorkerRow[]>([])
  const [loading, setLoading] = useState(false)

  const fetchWorkers = async () => {
    setLoading(true)
    try {
      const response: any = await apiClient.get('/workers')
      setWorkers(response.data || [])
    } catch (error) {
      message.error('加载 Worker 列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWorkers()
  }, [])

  const columns: ColumnsType<WorkerRow> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag color="purple">{type.toUpperCase()}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={statusColors[status] || 'default'}>{status}</Tag>
      ),
    },
    {
      title: '资源',
      key: 'resources',
      render: (_, record) =>
        `${record.cpu_cores} 核 / ${record.memory_gb}GB / ${record.gpu_count} GPU`,
    },
    {
      title: '完成/失败',
      key: 'jobs',
      render: (_, record) => `${record.jobs_completed} / ${record.jobs_failed}`,
    },
    {
      title: '最后心跳',
      dataIndex: 'last_heartbeat',
      key: 'last_heartbeat',
      render: (value: string | null) => (value ? new Date(value).toLocaleString() : '—'),
    },
  ]

  return (
    <Card title="Worker 管理">
      <Typography.Paragraph type="secondary">
        展示注册到编排器的 Worker 及其状态，数据来自 /api/v1/workers。
      </Typography.Paragraph>
      <Table<WorkerRow>
        rowKey="id"
        columns={columns}
        dataSource={workers}
        loading={loading}
        pagination={false}
      />
    </Card>
  )
}

export default Workers
