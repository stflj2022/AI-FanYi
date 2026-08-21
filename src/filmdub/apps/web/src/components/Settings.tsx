import React, { useEffect, useState } from 'react'
import { Card, Descriptions, Tag, Typography, message } from 'antd'
import apiClient from '@/services/api'

interface HealthInfo {
  status: string
  version: string
}

const Settings: React.FC = () => {
  const [health, setHealth] = useState<HealthInfo | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const fetchHealth = async () => {
      setLoading(true)
      try {
        const response: any = await apiClient.get('/health')
        setHealth(response.data)
      } catch (error) {
        message.error('无法连接后端服务')
      } finally {
        setLoading(false)
      }
    }
    fetchHealth()
  }, [])

  return (
    <Card title="系统设置" loading={loading}>
      <Descriptions bordered column={1} size="middle">
        <Descriptions.Item label="后端服务状态">
          {health ? (
            <Tag color="green">{health.status}</Tag>
          ) : (
            <Tag color="red">离线</Tag>
          )}
        </Descriptions.Item>
        <Descriptions.Item label="后端版本">
          {health?.version || '—'}
        </Descriptions.Item>
        <Descriptions.Item label="API 前缀">/api/v1</Descriptions.Item>
        <Descriptions.Item label="实时通信">
          WebSocket /ws（支持作业进度与系统事件推送）
        </Descriptions.Item>
      </Descriptions>
      <Typography.Paragraph type="secondary" style={{ marginTop: 16 }}>
        设置项可在后端环境变量中配置（数据库、MinIO、调度器等），本页面仅展示服务状态。
      </Typography.Paragraph>
    </Card>
  )
}

export default Settings
