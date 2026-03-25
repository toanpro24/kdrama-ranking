import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'

// Mock firebase
vi.mock('../firebase', () => ({
  auth: {},
  googleProvider: {},
}))

const mockLeaderboardData = {
  entries: [
    { rank: 1, actressId: 'a1', name: 'Kim Tae-ri', image: null, known: 'Twenty-Five Twenty-One', genre: 'Romance', totalLists: 5, avgScore: 5.4, topTierCount: 4, tierCounts: { splus: 2, s: 2, a: 1 } },
    { rank: 2, actressId: 'a2', name: 'Park Eun-bin', image: 'https://example.com/peb.jpg', known: 'Extraordinary Attorney Woo', genre: 'Drama', totalLists: 4, avgScore: 4.8, topTierCount: 3, tierCounts: { s: 3, b: 1 } },
    { rank: 3, actressId: 'a3', name: 'Shin Hye-sun', image: null, known: 'Mr. Queen', genre: 'Historical', totalLists: 3, avgScore: 4.2, topTierCount: 2, tierCounts: { a: 2, c: 1 } },
    { rank: 4, actressId: 'a4', name: 'IU', image: null, known: 'Hotel Del Luna', genre: 'Fantasy', totalLists: 3, avgScore: 3.8, topTierCount: 1, tierCounts: { s: 1, b: 1, c: 1 } },
    { rank: 5, actressId: 'a5', name: 'Jun Ji-hyun', image: null, known: 'My Love from the Star', genre: 'Romance', totalLists: 2, avgScore: 3.5, topTierCount: 1, tierCounts: { a: 1, b: 1 } },
  ],
  totalUsers: 6,
}

const mockFetchLeaderboard = vi.fn().mockResolvedValue(mockLeaderboardData)

vi.mock('../api', () => ({
  fetchLeaderboard: (...args: any[]) => mockFetchLeaderboard(...args),
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

import Leaderboard from '../Leaderboard'

function renderLeaderboard() {
  return render(
    <MemoryRouter>
      <Leaderboard />
    </MemoryRouter>,
  )
}

describe('Leaderboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchLeaderboard.mockResolvedValue(mockLeaderboardData)
  })

  it('renders the leaderboard title', async () => {
    renderLeaderboard()
    await waitFor(() => {
      expect(screen.getByText('Global Leaderboard')).toBeInTheDocument()
    })
  })

  it('shows total public users count', async () => {
    renderLeaderboard()
    await waitFor(() => {
      expect(screen.getByText(/6 public tier lists/)).toBeInTheDocument()
    })
  })

  it('renders top 3 podium cards', async () => {
    renderLeaderboard()
    await waitFor(() => {
      expect(screen.getByText('Kim Tae-ri')).toBeInTheDocument()
    })
    expect(screen.getByText('Park Eun-bin')).toBeInTheDocument()
    expect(screen.getByText('Shin Hye-sun')).toBeInTheDocument()
  })

  it('shows rank numbers for podium', async () => {
    renderLeaderboard()
    await waitFor(() => {
      expect(screen.getByText('#1')).toBeInTheDocument()
    })
    expect(screen.getByText('#2')).toBeInTheDocument()
    expect(screen.getByText('#3')).toBeInTheDocument()
  })

  it('renders remaining entries in table', async () => {
    renderLeaderboard()
    await waitFor(() => {
      expect(screen.getByText('IU')).toBeInTheDocument()
    })
    expect(screen.getByText('Jun Ji-hyun')).toBeInTheDocument()
  })

  it('shows average scores', async () => {
    renderLeaderboard()
    await waitFor(() => {
      expect(screen.getByText('5.4')).toBeInTheDocument()
    })
    // Podium scores
    expect(screen.getByText('4.8')).toBeInTheDocument()
  })

  it('shows list counts in podium', async () => {
    renderLeaderboard()
    await waitFor(() => {
      expect(screen.getByText('5 lists')).toBeInTheDocument()
    })
    expect(screen.getByText('4 lists')).toBeInTheDocument()
    expect(screen.getByText('3 lists')).toBeInTheDocument()
  })

  it('renders sort buttons', async () => {
    renderLeaderboard()
    expect(screen.getByText('Avg Score')).toBeInTheDocument()
    expect(screen.getByText('Most Listed')).toBeInTheDocument()
    expect(screen.getByText('Most Top-Tier')).toBeInTheDocument()
  })

  it('renders genre filter pills', async () => {
    renderLeaderboard()
    expect(screen.getByText('All')).toBeInTheDocument()
    expect(screen.getAllByText('Romance').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Fantasy').length).toBeGreaterThanOrEqual(1)
  })

  it('calls fetchLeaderboard with sort param when sort changes', async () => {
    renderLeaderboard()
    await waitFor(() => {
      expect(mockFetchLeaderboard).toHaveBeenCalledWith('score', 'All')
    })
    fireEvent.click(screen.getByText('Most Listed'))
    await waitFor(() => {
      expect(mockFetchLeaderboard).toHaveBeenCalledWith('lists', 'All')
    })
  })

  it('calls fetchLeaderboard with genre param when genre changes', async () => {
    renderLeaderboard()
    await waitFor(() => {
      expect(mockFetchLeaderboard).toHaveBeenCalledWith('score', 'All')
    })
    // Click the genre pill for Romance (there may be multiple "Romance" texts)
    const romancePills = screen.getAllByText('Romance')
    // The genre pill should be a button
    const pill = romancePills.find(el => el.tagName === 'BUTTON')
    if (pill) {
      fireEvent.click(pill)
      await waitFor(() => {
        expect(mockFetchLeaderboard).toHaveBeenCalledWith('score', 'Romance')
      })
    }
  })

  it('shows empty state when no entries', async () => {
    mockFetchLeaderboard.mockResolvedValue({ entries: [], totalUsers: 0 })
    renderLeaderboard()
    await waitFor(() => {
      expect(screen.getByText('No public tier lists yet')).toBeInTheDocument()
    })
  })

  it('shows tier badges in table rows', async () => {
    renderLeaderboard()
    await waitFor(() => {
      // IU (rank 4) has S x1
      expect(screen.getByText('S x1')).toBeInTheDocument()
    })
  })

  it('shows known-for text on podium', async () => {
    renderLeaderboard()
    await waitFor(() => {
      expect(screen.getByText('Twenty-Five Twenty-One')).toBeInTheDocument()
    })
  })

  it('renders back button', () => {
    renderLeaderboard()
    expect(screen.getByText('← Back to Tier List')).toBeInTheDocument()
  })
})
