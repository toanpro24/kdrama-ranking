import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'

// Mock firebase
vi.mock('../firebase', () => ({
  auth: {},
  googleProvider: {},
}))

const mockProfile = {
  _id: 'prof-1',
  userId: 'test-uid',
  displayName: 'Test User',
  bio: 'I love K-dramas!',
  shareSlug: 'test-user',
  tierListVisibility: 'private' as const,
  picture: 'https://example.com/pic.jpg',
}

const mockFetchProfile = vi.fn().mockResolvedValue(mockProfile)
const mockUpdateProfile = vi.fn().mockResolvedValue({ ...mockProfile, displayName: 'Updated Name' })

vi.mock('../api', () => ({
  fetchProfile: (...args: any[]) => mockFetchProfile(...args),
  updateProfile: (...args: any[]) => mockUpdateProfile(...args),
  setTokenGetter: vi.fn(),
}))

// Mock AuthContext — signed in by default
let mockUser: any = { uid: 'test-uid', displayName: 'Test User', email: 'test@test.com', photoURL: '' }
vi.mock('../AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    loading: false,
    signInWithGoogle: vi.fn(),
    logout: vi.fn(),
    getToken: async () => 'mock-token',
  }),
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

// Mock toast
vi.mock('../toast', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

import UserSettings from '../UserSettings'

function renderSettings() {
  return render(
    <MemoryRouter>
      <UserSettings />
    </MemoryRouter>,
  )
}

describe('UserSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUser = { uid: 'test-uid', displayName: 'Test User', email: 'test@test.com', photoURL: '' }
    mockFetchProfile.mockResolvedValue(mockProfile)
  })

  it('shows sign-in message when not authenticated', () => {
    mockUser = null
    renderSettings()
    expect(screen.getByText('Sign in to access settings')).toBeInTheDocument()
  })

  it('loads and displays profile data', async () => {
    renderSettings()
    await waitFor(() => {
      expect(screen.getByDisplayValue('Test User')).toBeInTheDocument()
    })
    expect(screen.getByDisplayValue('I love K-dramas!')).toBeInTheDocument()
    expect(screen.getByDisplayValue('test-user')).toBeInTheDocument()
  })

  it('renders visibility options', async () => {
    renderSettings()
    await waitFor(() => {
      expect(screen.getByText('Private')).toBeInTheDocument()
    })
    expect(screen.getByText('Link Only')).toBeInTheDocument()
    expect(screen.getByText('Public')).toBeInTheDocument()
  })

  it('shows save button disabled when no changes', async () => {
    renderSettings()
    await waitFor(() => {
      expect(screen.getByDisplayValue('Test User')).toBeInTheDocument()
    })
    const saveBtn = screen.getByText('Save Changes')
    expect(saveBtn).toBeDisabled()
  })

  it('enables save button when display name changes', async () => {
    const user = userEvent.setup()
    renderSettings()
    await waitFor(() => {
      expect(screen.getByDisplayValue('Test User')).toBeInTheDocument()
    })
    const nameInput = screen.getByDisplayValue('Test User')
    await user.clear(nameInput)
    await user.type(nameInput, 'New Name')
    const saveBtn = screen.getByText('Save Changes')
    expect(saveBtn).not.toBeDisabled()
  })

  it('calls updateProfile on save', async () => {
    const user = userEvent.setup()
    renderSettings()
    await waitFor(() => {
      expect(screen.getByDisplayValue('Test User')).toBeInTheDocument()
    })
    const nameInput = screen.getByDisplayValue('Test User')
    await user.clear(nameInput)
    await user.type(nameInput, 'New Name')
    const saveBtn = screen.getByText('Save Changes')
    await user.click(saveBtn)
    expect(mockUpdateProfile).toHaveBeenCalledWith({
      displayName: 'New Name',
      bio: 'I love K-dramas!',
      shareSlug: 'test-user',
      tierListVisibility: 'private',
    })
  })

  it('shows bio character count', async () => {
    renderSettings()
    await waitFor(() => {
      expect(screen.getByText(`${mockProfile.bio.length}/200`)).toBeInTheDocument()
    })
  })

  it('does not show copy link button when visibility is private', async () => {
    renderSettings()
    await waitFor(() => {
      expect(screen.getByDisplayValue('Test User')).toBeInTheDocument()
    })
    expect(screen.queryByText('Copy Share Link')).not.toBeInTheDocument()
  })

  it('shows copy link button when visibility is link_only', async () => {
    mockFetchProfile.mockResolvedValue({ ...mockProfile, tierListVisibility: 'link_only' })
    renderSettings()
    await waitFor(() => {
      expect(screen.getByText('Copy Share Link')).toBeInTheDocument()
    })
  })

  it('renders back button', async () => {
    renderSettings()
    await waitFor(() => {
      expect(screen.getByText('← Back to Tier List')).toBeInTheDocument()
    })
  })
})
