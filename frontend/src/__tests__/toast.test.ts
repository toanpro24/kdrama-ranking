import { describe, it, expect, beforeEach, vi } from 'vitest'
import { toast } from '../toast'

describe('toast', () => {
  beforeEach(() => {
    // Clean up any existing toast containers
    document.body.innerHTML = ''
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('creates a toast-container in the DOM', () => {
    toast('Hello')
    const container = document.querySelector('.toast-container')
    expect(container).toBeInTheDocument()
  })

  it('creates a toast element with the message', () => {
    toast('Test message')
    const toastEl = document.querySelector('.toast')
    expect(toastEl).toBeInTheDocument()
    expect(toastEl?.textContent).toContain('Test message')
  })

  it('creates an info toast by default', () => {
    toast('Info message')
    const toastEl = document.querySelector('.toast-info')
    expect(toastEl).toBeInTheDocument()
  })

  it('toast.error creates an error toast', () => {
    toast.error('Error occurred')
    const toastEl = document.querySelector('.toast-error')
    expect(toastEl).toBeInTheDocument()
    expect(toastEl?.textContent).toContain('Error occurred')
  })

  it('toast.success creates a success toast', () => {
    toast.success('Action completed')
    const toastEl = document.querySelector('.toast-success')
    expect(toastEl).toBeInTheDocument()
    expect(toastEl?.textContent).toContain('Action completed')
  })

  it('auto-removes toast after duration', () => {
    toast('Temporary', 'info', 1000)
    expect(document.querySelector('.toast')).toBeInTheDocument()

    // Advance past the duration
    vi.advanceTimersByTime(1000)
    // The toast-exit class is added, then removed after 300ms
    vi.advanceTimersByTime(300)
    expect(document.querySelector('.toast')).not.toBeInTheDocument()
  })

  it('reuses the same container for multiple toasts', () => {
    toast('First')
    toast('Second')
    const containers = document.querySelectorAll('.toast-container')
    expect(containers).toHaveLength(1)
    const toasts = document.querySelectorAll('.toast')
    expect(toasts).toHaveLength(2)
  })
})
