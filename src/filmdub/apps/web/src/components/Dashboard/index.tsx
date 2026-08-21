import React, { useEffect } from 'react'
import { Card, Row, Col, Statistic, List, Tag } from 'antd'
import { useProjectStore } from '@/store'

const Dashboard: React.FC = () => {
  const { projects, fetchProjects, loading } = useProjectStore()

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  const activeProjects = projects.filter((p) => p.status === 'active')
  const completedProjects = projects.filter((p) => p.status === 'completed')

  return (
    <div>
      <h2 className="mb-6 text-2xl font-bold">仪表盘</h2>

      <Row gutter={16} className="mb-6">
        <Col span={6}>
          <Card>
            <Statistic
              title="总项目数"
              value={projects.length}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="进行中"
              value={activeProjects.length}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已完成"
              value={completedProjects.length}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="活跃 Workers" value={0} />
          </Card>
        </Col>
      </Row>

      <Card title="最近项目" className="mb-6">
        <List
          dataSource={projects.slice(0, 5)}
          renderItem={(project) => (
            <List.Item>
              <List.Item.Meta
                title={project.name}
                description={project.description}
              />
              <Tag color={project.status === 'active' ? 'green' : 'blue'}>
                {project.status}
              </Tag>
            </List.Item>
          )}
          loading={loading}
        />
      </Card>
    </div>
  )
}

export default Dashboard
