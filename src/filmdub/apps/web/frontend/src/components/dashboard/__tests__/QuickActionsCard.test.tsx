import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { QuickActionsCard } from '../QuickActionsCard'
import { BrowserRouter } from 'react-router-dom'
import React from 'react'

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('QuickActionsCard', () => {
  it('渲染三个快速操作卡片', () => {
    const { container } = renderWithRouter(<QuickActionsCard />)

    expect(container.textContent).toContain('添加视频')
    expect(container.textContent).toContain('创建项目')
    expect(container.textContent).toContain('查看项目')
  })

  it('显示每个操作的描述', () => {
    renderWithRouter(<QuickActionsCard />)

    expect(screen.getByText('上传视频开始新的配音任务')).toBeInTheDocument()
    expect(screen.getByText('组织你的配音项目')).toBeInTheDocument()
    expect(screen.getByText('浏览所有项目')).toBeInTheDocument()
  })

  it('每个操作都有对应的按钮', () => {
    const { container } = renderWithRouter(<QuickActionsCard />)

    expect(container.textContent).toContain('添加视频')
    expect(container.textContent).toContain('创建项目')
    expect(container.textContent).toContain('查看项目')
  })
})
