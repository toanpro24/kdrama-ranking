import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { ReactNode } from 'react'

vi.mock('../firebase', () => ({
  auth: {},
  googleProvider: {},
}))

const mockCompareData = {
  users: [
    {
      displayName: 'Alice',
      picture: 'https://example.com/alice.jpg',
      shareSlug: 'alice',
      actresses: [
        { _id: 'a1', name: 'Kim Tae-ri', known: 'Twenty-Five', genre: 'Romance', year: 2022, tier: 'splus', image: null, birthDate: null, birthPlace: null, agency: null, dramas: [], awards: [], gallery: [] },
        { _id: 'a2', name: 'Park Eun-bin', known: 'Attorney Woo', genre: 'Drama', year: 2022, tier: 's', image: null, birthDate: null, birthPlace: null, agency: null, dramas: [], awards: [], gallery: [] },
        { _id: 'a3', name: 'Shin Hye-sun', known: 'Mr. Queen', genre: 'Historical', year: 2021, tier: 'a', image: null, birthDate: null, birthPlace: null, agency: null, dramas: [], awards: [], gallery: [] },
      ],
    },
    {
      displayName: 'Bob',
      picture: '',
      shareSlug: 'bob',
      actresses: [
        { _id: 'a1', name: 'Kim Tae-ri', known: 'Twenty-Five', genre: 'Romance', year: 2022, tier: 'splus', image: null, birthDate: null, birthPlace: null, agency: null, dramas: [], awards: [], gallery: [] },
        { _id: 'a2', name: 'Park Eun-bin', known: 'Attorney Woo', genre: 'Drama', year: 2022, tier: 'a', image: null, birthDate: null, birthPlace: null, agency: null, dramas: [], awards: [], gallery: [] },
        { _id: 'a4', name: 'IU', known: 'Hotel Del Luna', genre: 'Fantasy', year: 2019, tier: 's', image: null, birthDate: null, birthPlace: null, agency: null, dramas: [], awards: [], gallery: [] },
      ],
    },
  ],
  stats: {
    commonActresses: 2,
    exactMatches: 1,
    agreementPct: 50,
  },
}

const mockFetchCompare = vi.fn().mockResolvedValue(mockCompareData)

vi.mock('../api', () => ({
  fetchCompare: (...args: any[]) => mockFetchCompare(...args),
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

import CompareLists from '../CompareLists'

function renderCompare(slug1 = 'alice', slug2 = 'bob') {
  return render(
    <MemoryRouter initialEntries={[`/compare-lists/${slug1}/${slug2}`]}>
      <Routes>
        <Route path="/compare-lists/:slug1/:slug2" element={<CompareLists />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CompareLists', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchCompare.mockResolvedValue(mockCompareData)
  })

  it('shows loading state initially', () => {
    mockFetchCompare.mockReturnValue(new Promise(() => {}))
    renderCompare()
    expect(screen.getByText('Loading comparison...')).toBeInTheDocument()
  })

  it('renders comparison title', async () => {
    renderCompare()
    await waitFor(() => {
      expect(screen.getByText('Compare Tier Lists')).toBeInTheDocument()
    })
  })

  it('displays both user names', async () => {
    renderCompare()
    await waitFor(() => {
      expect(screen.getAllByText('Alice').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Bob').length).toBeGreaterThan(0)
    })
  })

  it('shows VS divider', async () => {
    renderCompare()
    await waitFor(() => {
      expect(screen.getByText('VS')).toBeInTheDocument()
    })
  })

  it('displays agreement stats', async () => {
    renderCompare()
    await waitFor(() => {
      expect(screen.getByText('50%')).toBeInTheDocument()
      expect(screen.getByText('Agreement')).toBeInTheDocument()
      expect(screen.getByText('1')).toBeInTheDocument()
      expect(screen.getByText('Exact Matches')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
      expect(screen.getByText('Common Actresses')).toBeInTheDocument()
    })
  })

  it('renders actress rows in comparison table', async () => {
    renderCompare()
    await waitFor(() => {
      expect(screen.getByText('Kim Tae-ri')).toBeInTheDocument()
      expect(screen.getByText('Park Eun-bin')).toBeInTheDocument()
      expect(screen.getByText('Shin Hye-sun')).toBeInTheDocument()
      expect(screen.getByText('IU')).toBeInTheDocument()
    })
  })

  it('calls fetchCompare with correct slugs', async () => {
    renderCompare('alice', 'bob')
    await waitFor(() => {
      expect(mockFetchCompare).toHaveBeenCalledWith('alice', 'bob')
    })
  })

  it('shows error state when comparison fails', async () => {
    mockFetchCompare.mockResolvedValue(null)
    renderCompare()
    await waitFor(() => {
      expect(screen.getByText(/Could not load comparison/)).toBeInTheDocument()
    })
  })

  it('shows back button', async () => {
    renderCompare()
    await waitFor(() => {
      expect(screen.getByText('← Back to Home')).toBeInTheDocument()
    })
  })

  it('displays user avatar when available', async () => {
    renderCompare()
    await waitFor(() => {
      const imgs = document.querySelectorAll('.cl-user-avatar')
      expect(imgs.length).toBe(1) // only Alice has a picture
      expect(imgs[0]).toHaveAttribute('src', 'https://example.com/alice.jpg')
    })
  })
})
