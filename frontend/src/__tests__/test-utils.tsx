import { render, type RenderOptions } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { createContext, useContext, type ReactNode } from 'react'
import type { Actress } from '../types'

// ---- Mock Auth Context ----
interface AuthContextType {
  user: { uid: string; displayName: string; email: string; photoURL: string } | null
  loading: boolean
  signInWithGoogle: () => Promise<void>
  logout: () => Promise<void>
  getToken: () => Promise<string | null>
}

const MockAuthContext = createContext<AuthContextType | null>(null)

export function MockAuthProvider({
  children,
  user = { uid: 'test-uid', displayName: 'Test User', email: 'test@test.com', photoURL: '' },
  loading = false,
}: {
  children: ReactNode
  user?: AuthContextType['user']
  loading?: boolean
}) {
  const value: AuthContextType = {
    user,
    loading,
    signInWithGoogle: async () => {},
    logout: async () => {},
    getToken: async () => 'mock-token',
  }
  return <MockAuthContext.Provider value={value}>{children}</MockAuthContext.Provider>
}

// ---- Mock Actress Context ----
interface ActressContextValue {
  actresses: Actress[]
  loading: boolean
  error: boolean
  reload: () => Promise<void>
  addActress: (actress: Actress) => void
  removeActress: (id: string) => void
  updateActressTier: (id: string, tier: string | null) => void
  updateDrama: (actressId: string, dramaTitle: string, field: "rating" | "watchStatus", value: number | string | null) => void
}

const MockActressContext = createContext<ActressContextValue | null>(null)

export function MockActressProvider({
  children,
  actresses = [],
  loading = false,
  error = false,
}: {
  children: ReactNode
  actresses?: Actress[]
  loading?: boolean
  error?: boolean
}) {
  const value: ActressContextValue = {
    actresses,
    loading,
    error,
    reload: async () => {},
    addActress: () => {},
    removeActress: () => {},
    updateActressTier: () => {},
    updateDrama: () => {},
  }
  return <MockActressContext.Provider value={value}>{children}</MockActressContext.Provider>
}

// ---- Combined wrapper ----
interface WrapperOptions {
  route?: string
  user?: AuthContextType['user']
  authLoading?: boolean
  actresses?: Actress[]
  actressLoading?: boolean
}

function createWrapper(options: WrapperOptions = {}) {
  const {
    route = '/',
    user = { uid: 'test-uid', displayName: 'Test User', email: 'test@test.com', photoURL: '' },
    authLoading = false,
    actresses = [],
    actressLoading = false,
  } = options

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter initialEntries={[route]}>
        <MockAuthProvider user={user} loading={authLoading}>
          <MockActressProvider actresses={actresses} loading={actressLoading}>
            {children}
          </MockActressProvider>
        </MockAuthProvider>
      </MemoryRouter>
    )
  }
}

export function renderWithProviders(
  ui: React.ReactElement,
  options: WrapperOptions & Omit<RenderOptions, 'wrapper'> = {},
) {
  const { route, user, authLoading, actresses, actressLoading, ...renderOptions } = options
  return render(ui, {
    wrapper: createWrapper({ route, user, authLoading, actresses, actressLoading }),
    ...renderOptions,
  })
}

// Re-export everything from testing-library
export * from '@testing-library/react'
export { default as userEvent } from '@testing-library/user-event'

// ---- Test data factories ----
export function createMockActress(overrides: Partial<Actress> = {}): Actress {
  return {
    _id: 'act-1',
    name: 'Kim Tae-ri',
    known: 'Twenty-Five Twenty-One',
    genre: 'Romance',
    year: 2022,
    tier: 's',
    image: null,
    birthDate: '1990-04-24',
    birthPlace: 'Seoul, South Korea',
    agency: 'Management SOOP',
    dramas: [
      {
        title: 'Twenty-Five Twenty-One',
        year: 2022,
        role: 'Na Hee-do',
        poster: null,
        rating: 9,
        watchStatus: 'watched',
        category: 'drama',
      },
    ],
    awards: ['Best Actress 2022'],
    gallery: [],
    ...overrides,
  }
}

export function createMockActressList(): Actress[] {
  return [
    createMockActress(),
    createMockActress({
      _id: 'act-2',
      name: 'Park Eun-bin',
      known: 'Extraordinary Attorney Woo',
      genre: 'Drama',
      year: 2022,
      tier: 'a',
      birthDate: '1992-09-04',
      dramas: [
        {
          title: 'Extraordinary Attorney Woo',
          year: 2022,
          role: 'Woo Young-woo',
          poster: null,
          rating: 8,
          watchStatus: 'watched',
          category: 'drama',
        },
        {
          title: 'The Kings Affection',
          year: 2021,
          role: 'Lee Hwi',
          poster: null,
          rating: 7,
          watchStatus: 'watched',
          category: 'drama',
        },
      ],
      awards: [],
      gallery: [],
    }),
    createMockActress({
      _id: 'act-3',
      name: 'Shin Hye-sun',
      known: 'Mr. Queen',
      genre: 'Historical',
      year: 2021,
      tier: null,
      birthDate: null,
      dramas: [],
      awards: [],
      gallery: [],
    }),
  ]
}
