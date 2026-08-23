import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { JobStatsCard } from '../JobStatsCard'

describe('JobStatsCard', () => {
  const mockStats = {
    total: 100,
    pending: 10,
    scheduled: 20,
    running: 5,
    waiting: 3,
    completed: 50,
    failed: 10,
    cancelled: 2,
    retrying: 2,
    active: 7,
    finished: 62,
  }

  it('渲染统计数据', () => {
    render(<JobStatsCard stats={mockStats} />)

    expect(screen.getByText('总任务')).toBeInTheDocument()
    expect(screen.getByText('100')).toBeInTheDocument()
    expect(screen.getByText('运行中')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByText('已完成')).toBeInTheDocument()
    expect(screen.getByText('50')).toBeInTheDocument()
    expect(screen.getByText('失败')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
  })

  it('显示加载状态', () => {
    render(<JobStatsCard stats={mockStats} loading={true} />)

    // 应该显示骨架屏
    const skeletons = document.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('正确计算活跃任务数', () => {
    render(<JobStatsCard stats={mockStats} />)

    // active = running + retrying = 5 + 2 = 7
    expect(screen.getByText('7')).toBeInTheDocument()
  })


})
