import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { JobProgressBar } from '../JobProgressBar'

describe('JobProgressBar', () => {
  it('should render progress bar with percentage', () => {
    render(<JobProgressBar progress={50} />)

    expect(screen.getByText('50%')).toBeInTheDocument()
  })

  it('should render stage when showStage is true', () => {
    render(
      <JobProgressBar
        progress={50}
        stage="processing"
        showStage={true}
      />
    )

    expect(screen.getByText(/阶段:/i)).toBeInTheDocument()
    expect(screen.getByText('processing')).toBeInTheDocument()
  })

  it('should not render stage when showStage is false', () => {
    render(
      <JobProgressBar
        progress={50}
        stage="processing"
        showStage={false}
      />
    )

    expect(screen.queryByText(/阶段:/i)).not.toBeInTheDocument()
  })

  it('should render message when showMessage is true', () => {
    render(
      <JobProgressBar
        progress={50}
        message="Processing video..."
        showMessage={true}
      />
    )

    expect(screen.getByText('Processing video...')).toBeInTheDocument()
  })

  it('should not render message when showMessage is false', () => {
    render(
      <JobProgressBar
        progress={50}
        message="Processing video..."
        showMessage={false}
      />
    )

    expect(screen.queryByText('Processing video...')).not.toBeInTheDocument()
  })

  it('should render all information', () => {
    render(
      <JobProgressBar
        progress={75}
        stage="encoding"
        message="Encoding video..."
        showStage={true}
        showMessage={true}
      />
    )

    expect(screen.getByText('75%')).toBeInTheDocument()
    expect(screen.getByText(/阶段:/i)).toBeInTheDocument()
    expect(screen.getByText('Encoding video...')).toBeInTheDocument()
    // Stage text might be in a nested element
    expect(screen.getByText(/encoding/)).toBeInTheDocument()
  })

  it('should handle zero progress', () => {
    render(<JobProgressBar progress={0} />)

    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('should handle full progress', () => {
    render(<JobProgressBar progress={100} />)

    expect(screen.getByText('100%')).toBeInTheDocument()
  })

  it('should render without stage and message by default', () => {
    const { container } = render(<JobProgressBar progress={50} />)

    expect(screen.queryByText(/阶段:/i)).not.toBeInTheDocument()
    expect(container.textContent).toContain('50%')
  })
})
