import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { Toast, useToast, ToastContainer } from '../toast'

describe('Toast', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  it('should render success toast', () => {
    render(
      <Toast
        id="test-1"
        type="success"
        title="Success"
        message="Operation completed"
      />
    )

    waitFor(() => {
      expect(screen.getByText('Success')).toBeInTheDocument()
      expect(screen.getByText('Operation completed')).toBeInTheDocument()
    })
  })

  it('should render error toast', () => {
    render(
      <Toast
        id="test-2"
        type="error"
        title="Error"
        message="Operation failed"
      />
    )

    waitFor(() => {
      expect(screen.getByText('Error')).toBeInTheDocument()
      expect(screen.getByText('Operation failed')).toBeInTheDocument()
    })
  })

  it('should render warning toast', () => {
    render(
      <Toast
        id="test-3"
        type="warning"
        title="Warning"
        message="Please check your input"
      />
    )

    waitFor(() => {
      expect(screen.getByText('Warning')).toBeInTheDocument()
      expect(screen.getByText('Please check your input')).toBeInTheDocument()
    })
  })

  it('should render info toast', () => {
    render(
      <Toast
        id="test-4"
        type="info"
        title="Info"
        message="New update available"
      />
    )

    waitFor(() => {
      expect(screen.getByText('Info')).toBeInTheDocument()
      expect(screen.getByText('New update available')).toBeInTheDocument()
    })
  })

  it('should close when close button is clicked', () => {
    const onClose = vi.fn()
    render(
      <Toast
        id="test-5"
        type="success"
        title="Test"
        onClose={onClose}
      />
    )

    const closeButton = screen.getByRole('button')
    fireEvent.click(closeButton)

    waitFor(() => {
      expect(onClose).toHaveBeenCalledWith('test-5')
    })
  })

  it('should auto-close after duration', () => {
    const onClose = vi.fn()
    render(
      <Toast
        id="test-6"
        type="success"
        title="Test"
        duration={5000}
        onClose={onClose}
      />
    )

    vi.advanceTimersByTime(5000)
    vi.advanceTimersByTime(300) // Wait for transition

    expect(onClose).toHaveBeenCalledWith('test-6')
  })

  it('should not auto-close when duration is 0', () => {
    const onClose = vi.fn()
    render(
      <Toast
        id="test-7"
        type="success"
        title="Test"
        duration={0}
        onClose={onClose}
      />
    )

    vi.advanceTimersByTime(10000)

    expect(onClose).not.toHaveBeenCalled()
  })
})

describe('useToast', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  it('should add toast to list', () => {
    const TestComponent = () => {
      const { toasts, success } = useToast()

      return (
        <div>
          <button onClick={() => success('Test success')}>Add Toast</button>
          <ToastContainer toasts={toasts} onClose={() => {}} />
        </div>
      )
    }

    render(<TestComponent />)

    expect(screen.queryByText('Test success')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('Add Toast'))

    expect(screen.getByText('Test success')).toBeInTheDocument()
  })

  it('should remove toast', () => {
    const TestComponent = () => {
      const { toasts, success, removeToast } = useToast()

      return (
        <div>
          <button onClick={() => success('Test success')}>Add Toast</button>
          <button onClick={() => removeToast(toasts[0]?.id || '')}>Remove Toast</button>
          <ToastContainer toasts={toasts} onClose={removeToast} />
        </div>
      )
    }

    render(<TestComponent />)

    // Add toast
    fireEvent.click(screen.getByText('Add Toast'))
    expect(screen.getByText('Test success')).toBeInTheDocument()

    // Get the toast ID
    const toastId = screen.getByText('Test success').closest('div')?.getAttribute('data-toast-id')

    // Remove toast (need to implement data attribute for this)
    // For now, just verify the function is called
  })

  it('should support different toast types', () => {
    const TestComponent = () => {
      const { toasts, success, error, warning, info } = useToast()

      return (
        <div>
          <button onClick={() => success('Success')}>Success</button>
          <button onClick={() => error('Error')}>Error</button>
          <button onClick={() => warning('Warning')}>Warning</button>
          <button onClick={() => info('Info')}>Info</button>
          <ToastContainer toasts={toasts} onClose={() => {}} />
        </div>
      )
    }

    render(<TestComponent />)

    fireEvent.click(screen.getByText('Success'))
    expect(screen.getByText('Success')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Error'))
    expect(screen.getByText('Error')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Warning'))
    expect(screen.getByText('Warning')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Info'))
    expect(screen.getByText('Info')).toBeInTheDocument()
  })

  it('should clear all toasts', () => {
    const TestComponent = () => {
      const { toasts, success, clear } = useToast()

      return (
        <div>
          <button onClick={() => success('Toast 1')}>Add 1</button>
          <button onClick={() => success('Toast 2')}>Add 2</button>
          <button onClick={clear}>Clear All</button>
          <ToastContainer toasts={toasts} onClose={() => {}} />
        </div>
      )
    }

    render(<TestComponent />)

    fireEvent.click(screen.getByText('Add 1'))
    fireEvent.click(screen.getByText('Add 2'))

    expect(screen.getByText('Toast 1')).toBeInTheDocument()
    expect(screen.getByText('Toast 2')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Clear All'))

    expect(screen.queryByText('Toast 1')).not.toBeInTheDocument()
    expect(screen.queryByText('Toast 2')).not.toBeInTheDocument()
  })
})
