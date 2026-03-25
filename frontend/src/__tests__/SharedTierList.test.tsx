import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { ReactNode } from 'react'

// Mock firebase
vi.mock('../firebase', () => ({
  auth: {},
  googleProvider: {},
}))

const mockSharedData = {
  displayName: 'Jane',
  bio: 'K-Drama fan since 2020',
  picture: 'https://example.com/jane.jpg',
  actresses: [
    { _id: 'a1', name: 'Kim Tae-ri', known: 'Twenty-Five Twenty-One', genre: 'Romance', year: 2022, tier: 'splus', image: null, birthDate: null, birthPlace: null, agency: null, dramas: [], awards: [], gallery: [] },
    { _id: 'a2', name: 'Park Eun-bin', known: 'Extraordinary Attorney Woo', genre: 'Drama', year: 2022, tier: 's', image: null, birthDate: null, birthPlace: null, agency: null, dramas: [], awards: [], gallery: [] },
    { _id: 'a3', name: 'Shin Hye-sun', known: 'Mr. Queen', genre: 'Historical', year: 2021, tier: null, image: null, birthDate: null, birthPlace: null, agency: null, dramas: [], awards: [], gallery: [] },
  ],
}

const mockFetchSharedTierList = vi.fn().mockResolvedValue(mockSharedData)

vi.mock('../api', () => ({
  fetchSharedTierList: (...args: any[]) => mockFetchSharedTierList(...args),
  setTokenGetter: vi.fn(),
}))

vi.mock('../AuthContext', () => ({
  useAuth: () => ({
    user: null,
    loading: false,
    signInWithGoogle: vi.fn(),
    logout: vi.fn(),
    getToken: async () => null,
  }),
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

import SharedTierList from '../SharedTierList'

function renderShared(slug = 'jane') {
  return render(
    <MemoryRouter initialEntries={[`/tier-list/${slug}`]}>
      <Routes>
        <Route path="/tier-list/:slug" element={<SharedTierList />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('SharedTierList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchSharedTierList.mockResolvedValue(mockSharedData)
  })

  it('fetches tier list by slug', async () => {
    renderShared('jane')
    await waitFor(() => {
      expect(mockFetchSharedTierList).toHaveBeenCalledWith('jane')
    })
  })

  it('displays user name and bio', async () => {
    renderShared()
    await waitFor(() => {
      expect(screen.getByText("Jane's Tier List")).toBeInTheDocument()
    })
    expect(screen.getByText('K-Drama fan since 2020')).toBeInTheDocument()
  })

  it('shows ranked count', async () => {
    renderShared()
    await waitFor(() => {
      expect(screen.getByText('2 ranked out of 3 actresses')).toBeInTheDocument()
    })
  })

  it('renders tier rows with labels', async () => {
    renderShared()
    await waitFor(() => {
      expect(screen.getByText('S+')).toBeInTheDocument()
    })
    expect(screen.getByText('S')).toBeInTheDocument()
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
    expect(screen.getByText('C')).toBeInTheDocument()
    expect(screen.getByText('D')).toBeInTheDocument()
  })

  it('shows actresses in correct tiers', async () => {
    renderShared()
    await waitFor(() => {
      expect(screen.getByText('Kim Tae-ri')).toBeInTheDocument()
    })
    expect(screen.getByText('Park Eun-bin')).toBeInTheDocument()
  })

  it('shows error when tier list not found', async () => {
    mockFetchSharedTierList.mockResolvedValue(null)
    renderShared('nonexistent')
    await waitFor(() => {
      expect(screen.getByText("This tier list doesn't exist or is private.")).toBeInTheDocument()
    })
  })

  it('shows user avatar when picture provided', async () => {
    renderShared()
    await waitFor(() => {
      expect(screen.getByText("Jane's Tier List")).toBeInTheDocument()
    })
    const avatar = document.querySelector('.shared-avatar') as HTMLImageElement
    expect(avatar).toBeTruthy()
    expect(avatar.src).toBe('https://example.com/jane.jpg')
  })

  it('shows placeholder initial when actress has no image', async () => {
    renderShared()
    await waitFor(() => {
      expect(screen.getByText('K')).toBeInTheDocument() // Kim Tae-ri initial
    })
  })

  it('shows back button', async () => {
    renderShared()
    await waitFor(() => {
      expect(screen.getByText('← Back to Home')).toBeInTheDocument()
    })
  })

  it('updates page title with user name', async () => {
    renderShared()
    await waitFor(() => {
      expect(document.title).toBe("Jane's K-Drama Tier List")
    })
  })
})
