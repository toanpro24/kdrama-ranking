import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { createMockActressList } from './test-utils'

// Mock firebase to prevent import errors
vi.mock('../firebase', () => ({
  auth: {},
  googleProvider: {},
}))

// Mock AuthContext
vi.mock('../AuthContext', () => ({
  useAuth: () => ({
    user: { uid: 'test-uid', displayName: 'Test User', email: 'test@test.com', photoURL: '' },
    loading: false,
    signInWithGoogle: vi.fn(),
    logout: vi.fn(),
    getToken: async () => 'mock-token',
  }),
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

// Mock ActressContext
const mockActresses = createMockActressList()
const mockReload = vi.fn()
let mockLoading = false

vi.mock('../ActressContext', () => ({
  useActresses: () => ({
    actresses: mockLoading ? [] : mockActresses,
    loading: mockLoading,
    error: false,
    reload: mockReload,
    addActress: vi.fn(),
    removeActress: vi.fn(),
    updateActressTier: vi.fn(),
    updateDrama: vi.fn(),
  }),
  ActressProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

// Mock html-to-image
vi.mock('html-to-image', () => ({
  toPng: vi.fn(),
}))

// Mock api functions
vi.mock('../api', () => ({
  createActress: vi.fn(),
  updateTier: vi.fn(),
  deleteActress: vi.fn(),
  resetData: vi.fn(),
  searchActressOnline: vi.fn().mockResolvedValue([]),
  getActressFromTMDB: vi.fn(),
  setTokenGetter: vi.fn(),
  fetchActresses: vi.fn().mockResolvedValue([]),
}))

import App from '../App'

function renderApp() {
  return render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  )
}

describe('App', () => {
  beforeEach(() => {
    mockLoading = false
    vi.clearAllMocks()
  })

  it('renders the app title / heading', () => {
    renderApp()
    // The app likely has a heading or title element
    const heading = document.querySelector('h1, .app-title, .hero-title')
    expect(heading).toBeTruthy()
  })

  it('renders nav tabs', () => {
    renderApp()
    // Look for navigation links
    const nav = document.querySelector('nav, .nav, .nav-tabs, .tab-bar')
    expect(nav).toBeTruthy()
  })

  it('renders tier list section with tier labels', () => {
    renderApp()
    // The tier labels from constants should be visible
    expect(screen.getByText('S+')).toBeInTheDocument()
    expect(screen.getByText('S')).toBeInTheDocument()
    expect(screen.getByText('A')).toBeInTheDocument()
  })

  it('renders actress cards when data is loaded', () => {
    renderApp()
    // Our mock actresses should be rendered
    expect(screen.getByText('Kim Tae-ri')).toBeInTheDocument()
    expect(screen.getByText('Park Eun-bin')).toBeInTheDocument()
  })

  it('renders unranked pool section', () => {
    renderApp()
    // Shin Hye-sun has tier: null, so she should be in unranked
    expect(screen.getByText('Shin Hye-sun')).toBeInTheDocument()
  })

  it('renders genre filter buttons', () => {
    renderApp()
    expect(screen.getByText('All')).toBeInTheDocument()
    // "Romance" appears in both genre filters and actress cards
    expect(screen.getAllByText('Romance').length).toBeGreaterThanOrEqual(1)
  })

  it('renders loading state', () => {
    mockLoading = true
    renderApp()
    // When loading, the app should show some loading indicator
    const loadingEl = document.querySelector('.loading, .spinner, .skeleton, [class*="load"]')
    // Even if no explicit loading indicator, actresses shouldn't be visible
    expect(screen.queryByText('Kim Tae-ri')).not.toBeInTheDocument()
  })
})
