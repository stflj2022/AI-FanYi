import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { JobStageDisplay } from '../JobStageDisplay'

describe('JobStageDisplay', () => {
  it('should render current stage only', () => {
    render(<JobStageDisplay currentStage="processing" />)

    expect(screen.getByText('processing')).toBeInTheDocument()
  })

  it('should render current and previous stage', () => {
    render(
      <JobStageDisplay
        currentStage="encoding"
        previousStage="processing"
      />
    )

    // Use getAllByText to find both stages
    const stages = screen.getAllByText(/processing|encoding/)
    expect(stages).toHaveLength(2)
  })

  it('should render waiting message when no stage', () => {
    render(<JobStageDisplay />)

    expect(screen.getByText('等待开始...')).toBeInTheDocument()
  })

  it('should render stages list', () => {
    const stages = [
      { id: '1', name: '上传', status: 'completed' as const },
      { id: '2', name: '处理', status: 'in_progress' as const },
      { id: '3', name: '编码', status: 'pending' as const },
      { id: '4', name: '完成', status: 'pending' as const },
    ]

    render(<JobStageDisplay stages={stages} />)

    expect(screen.getByText('上传')).toBeInTheDocument()
    expect(screen.getByText('处理')).toBeInTheDocument()
    expect(screen.getByText('编码')).toBeInTheDocument()
    expect(screen.getByText('完成')).toBeInTheDocument()
  })

  it('should render different sizes', () => {
    const { rerender } = render(
      <JobStageDisplay currentStage="processing" size="sm" />
    )
    const smallContainer = screen.getByText('processing').parentElement
    expect(smallContainer).toHaveClass('text-xs')

    rerender(<JobStageDisplay currentStage="processing" size="md" />)
    const mediumContainer = screen.getByText('processing').parentElement
    expect(mediumContainer).toHaveClass('text-sm')

    rerender(<JobStageDisplay currentStage="processing" size="lg" />)
    const largeContainer = screen.getByText('processing').parentElement
    expect(largeContainer).toHaveClass('text-base')
  })

  it('should show correct icons for stage statuses', () => {
    const stages = [
      { id: '1', name: '已完成', status: 'completed' as const },
      { id: '2', name: '进行中', status: 'in_progress' as const },
      { id: '3', name: '等待中', status: 'pending' as const },
      { id: '4', name: '失败', status: 'failed' as const },
    ]

    render(<JobStageDisplay stages={stages} />)

    // Check that all stages are rendered
    expect(screen.getByText('已完成')).toBeInTheDocument()
    expect(screen.getByText('进行中')).toBeInTheDocument()
    expect(screen.getByText('等待中')).toBeInTheDocument()
    expect(screen.getByText('失败')).toBeInTheDocument()
  })
})
