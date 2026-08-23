import { render, screen } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import { HealthCheck } from '../src/pages/HealthCheck'
import { JSDOM } from 'jsdom'

// 手动设置 jsdom 环境
global.document = new JSDOM('<!DOCTYPE html><html><body></body></html>').window.document
global.window = new JSDOM('<!DOCTYPE html><html><body></body></html>').window as any
global.navigator = window.navigator

describe('HealthCheck', () => {
  it('renders loading state', () => {
    render(<HealthCheck />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })
})
