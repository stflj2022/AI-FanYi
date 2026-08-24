import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { RecentJobsList } from '../RecentJobsList'
import { BrowserRouter } from 'react-router-dom'
import React from 'react'

const mockJobs = [
  {
    id: '1',
    name: '测试任务 1',
    status: 'running' as const,
    description: '这是一个测试任务',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    started_at: '2024-01-01T01:00:00Z',
    project_id: 'project-1',
    module_id: 'module-1',
    retry_count: 0,
    max_retries: 3,
  },
  {
    id: '2',
    name: '测试任务 2',
    status: 'completed' as const,
    description: '另一个测试任务',
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    completed_at: '2024-01-02T02:00:00Z',
    project_id: 'project-1',
    retry_count: 0,
    max_retries: 3,
  },
  {
    id: '3',
    name: '测试任务 3',
    status: 'failed' as const,
    description: '失败的任务',
    error_message: '出错了',
    created_at: '2024-01-03T00:00:00Z',
    updated_at: '2024-01-03T00:00:00Z',
    completed_at: '2024-01-03T01:00:00Z',
    project_id: 'project-1',
    retry_count: 1,
    max_retries: 3,
  },
]

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('RecentJobsList', () => {
  it('渲染任务列表', () => {
    renderWithRouter(<RecentJobsList jobs={mockJobs} />)

    expect(screen.getByText('最近任务')).toBeInTheDocument()
    expect(screen.getByText('测试任务 1')).toBeInTheDocument()
    expect(screen.getByText('测试任务 2')).toBeInTheDocument()
    expect(screen.getByText('测试任务 3')).toBeInTheDocument()
  })

  it('显示任务状态', () => {
    renderWithRouter(<RecentJobsList jobs={mockJobs} />)

    expect(screen.getByText('运行中')).toBeInTheDocument()
    expect(screen.getByText('已完成')).toBeInTheDocument()
    expect(screen.getByText('失败')).toBeInTheDocument()
  })

  it('显示任务描述', () => {
    renderWithRouter(<RecentJobsList jobs={mockJobs} />)

    expect(screen.getByText('这是一个测试任务')).toBeInTheDocument()
    expect(screen.getByText('另一个测试任务')).toBeInTheDocument()
    expect(screen.getByText('失败的任务')).toBeInTheDocument()
  })

  it('显示空状态', () => {
    renderWithRouter(<RecentJobsList jobs={[]} />)

    expect(screen.getByText('暂无任务')).toBeInTheDocument()
    expect(screen.getByText('还没有创建任何配音任务，点击上方按钮开始吧！')).toBeInTheDocument()
    expect(screen.getByText('上传视频')).toBeInTheDocument()
  })

  it('显示加载状态', () => {
    renderWithRouter(<RecentJobsList jobs={[]} loading={true} />)

    // 应该显示骨架屏
    const skeletons = document.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('显示"查看全部"链接', () => {
    const { container } = renderWithRouter(<RecentJobsList jobs={mockJobs} />)

    expect(container.textContent).toContain('查看全部')
  })
})
