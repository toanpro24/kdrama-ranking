import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'

// Mock firebase
vi.mock('../firebase', () => ({
  auth: {},
  googleProvider: {},
}))

const mockFollowing = [
  { userId: 'u1', displayName: 'Alice', picture: 'https://example.com/alice.jpg', shareSlug: 'alice', bio: 'K-drama fan', rankedCount: 15 },
  { userId: 'u2', displayName: 'Bob', picture: '', shareSlug: 'bob', bio: '', rankedCount: 8 },
]

const mockCounts = { followers: 3, following: 2 }

const mockFetchFollowing = vi.fn().mockResolvedValue(mockFollowing)
const mockFetchFollowerCount = vi.fn().mockResolvedValue(mockCounts)
const mockUnfollowUser = vi.fn().mockResolvedValue(true)

vi.mock('../api', () => ({
  fetchFollowing: (...args: any[]) => mockFetchFollowing(...args),
  fetchFollowerCount: (...args: any[]) => mockFetchFollowerCount(...args),
  unfollowUser: (...args: any[]) => mockUnfollowUser(...args),
  setTokenGetter: vi.fn(),
}))

const mockUser = { uid: 'test-user', name: 'Test' }
let mockAuthUser: typeof mockUser | null = mockUser

vi.mock('../AuthContext', () => ({
  useAuth: () => ({
    user: mockAuthUser,
    loading: false,
    signInWithGoogle: vi.fn(),
    logout: vi.fn(),
    getToken: async () => 'token',
  }),
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

import FollowingPage from '../FollowingPage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

function renderPage() {
  return render(
    <MemoryRouter>
      <FollowingPage />
    </MemoryRouter>,
  )
}

describe('FollowingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAuthUser = mockUser
    mockFetchFollowing.mockResolvedValue(mockFollowing)
    mockFetchFollowerCount.mockResolvedValue(mockCounts)
    mockUnfollowUser.mockResolvedValue(true)
  })

  it('renders the title', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Following')
    })
  })

  it('shows follower and following counts', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
      expect(screen.getByText('Followers')).toBeInTheDocument()
    })
  })

  it('renders following user cards', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument()
      expect(screen.getByText('Bob')).toBeInTheDocument()
    })
  })

  it('shows bio and ranked count', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('K-drama fan')).toBeInTheDocument()
      expect(screen.getByText('15 ranked')).toBeInTheDocument()
      expect(screen.getByText('8 ranked')).toBeInTheDocument()
    })
  })

  it('unfollows a user when clicking unfollow', async () => {
    renderPage()
    await waitFor(() => screen.getByText('Alice'))
    const unfollowBtns = screen.getAllByText('Unfollow')
    fireEvent.click(unfollowBtns[0])
    await waitFor(() => {
      expect(mockUnfollowUser).toHaveBeenCalledWith('alice')
    })
  })

  it('navigates to tier list on card click', async () => {
    renderPage()
    await waitFor(() => screen.getByText('Alice'))
    fireEvent.click(screen.getByText('Alice'))
    expect(mockNavigate).toHaveBeenCalledWith('/tier-list/alice')
  })

  it('shows empty state when not following anyone', async () => {
    mockFetchFollowing.mockResolvedValue([])
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("You're not following anyone yet.")).toBeInTheDocument()
    })
  })

  it('shows sign-in message for unauthenticated users', async () => {
    mockAuthUser = null
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Sign in to see your following list')).toBeInTheDocument()
    })
  })

  it('shows compare button for each user', async () => {
    renderPage()
    await waitFor(() => {
      const compareBtns = screen.getAllByText('Compare')
      expect(compareBtns).toHaveLength(2)
    })
  })

  it('shows placeholder avatar when no picture', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('B')).toBeInTheDocument() // Bob's placeholder
    })
  })
})
