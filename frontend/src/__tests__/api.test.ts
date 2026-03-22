import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { fetchActresses, fetchActress, createActress, rateDrama, updateWatchStatus, updateTier, deleteActress, setTokenGetter } from '../api'
import { createMockActress } from './test-utils'

const BASE = 'http://localhost:8000/api'

const mockActress = createMockActress()
const mockActressList = [mockActress]

const server = setupServer(
  http.get(`${BASE}/actresses`, () => {
    return HttpResponse.json(mockActressList)
  }),
  http.get(`${BASE}/actresses/:id`, ({ params }) => {
    if (params.id === 'act-1') {
      return HttpResponse.json(mockActress)
    }
    return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
  }),
  http.post(`${BASE}/actresses`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({ ...mockActress, name: body.name as string })
  }),
  http.patch(`${BASE}/actresses/:id/tier`, () => {
    return HttpResponse.json({ success: true })
  }),
  http.delete(`${BASE}/actresses/:id`, () => {
    return HttpResponse.json({ success: true })
  }),
  http.patch(`${BASE}/actresses/:actressId/dramas/:title/rating`, () => {
    return HttpResponse.json({ success: true })
  }),
  http.patch(`${BASE}/actresses/:actressId/dramas/:title/watch-status`, () => {
    return HttpResponse.json({ success: true })
  }),
)

beforeAll(() => {
  setTokenGetter(async () => 'test-token')
  server.listen({ onUnhandledRequest: 'bypass' })
})
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('api', () => {
  describe('fetchActresses', () => {
    it('returns an array of actresses', async () => {
      const result = await fetchActresses()
      expect(result).toEqual(mockActressList)
    })

    it('returns empty array on error', async () => {
      server.use(
        http.get(`${BASE}/actresses`, () => {
          return HttpResponse.json({ detail: 'Server error' }, { status: 500 })
        }),
      )
      const result = await fetchActresses()
      expect(result).toEqual([])
    })

    it('passes genre filter param', async () => {
      let capturedUrl = ''
      server.use(
        http.get(`${BASE}/actresses`, ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([])
        }),
      )
      await fetchActresses('Romance')
      expect(capturedUrl).toContain('genre=Romance')
    })

    it('passes search param', async () => {
      let capturedUrl = ''
      server.use(
        http.get(`${BASE}/actresses`, ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json([])
        }),
      )
      await fetchActresses(undefined, 'Kim')
      expect(capturedUrl).toContain('search=Kim')
    })
  })

  describe('fetchActress', () => {
    it('returns a single actress by id', async () => {
      const result = await fetchActress('act-1')
      expect(result).toEqual(mockActress)
    })

    it('returns null on 404', async () => {
      const result = await fetchActress('nonexistent')
      expect(result).toBeNull()
    })
  })

  describe('createActress', () => {
    it('sends correct data and returns actress', async () => {
      const data = { name: 'New Actress', known: 'Some Drama', genre: 'Romance', year: 2023 }
      const result = await createActress(data)
      expect(result).not.toBeNull()
      expect(result?.name).toBe('New Actress')
    })

    it('returns null on error', async () => {
      server.use(
        http.post(`${BASE}/actresses`, () => {
          return HttpResponse.json({ detail: 'Validation error' }, { status: 400 })
        }),
      )
      const result = await createActress({ name: '', known: '', genre: '', year: 0 })
      expect(result).toBeNull()
    })
  })

  describe('rateDrama', () => {
    it('sends PATCH with rating and returns true', async () => {
      const result = await rateDrama('act-1', 'Twenty-Five Twenty-One', 9)
      expect(result).toBe(true)
    })

    it('returns false on error', async () => {
      server.use(
        http.patch(`${BASE}/actresses/:id/dramas/:title/rating`, () => {
          return HttpResponse.json({ detail: 'Error' }, { status: 500 })
        }),
      )
      const result = await rateDrama('act-1', 'SomeDrama', 5)
      expect(result).toBe(false)
    })
  })

  describe('updateWatchStatus', () => {
    it('sends PATCH with status and returns true', async () => {
      const result = await updateWatchStatus('act-1', 'Twenty-Five Twenty-One', 'watched')
      expect(result).toBe(true)
    })

    it('returns false on error', async () => {
      server.use(
        http.patch(`${BASE}/actresses/:id/dramas/:title/watch-status`, () => {
          return HttpResponse.json({ detail: 'Error' }, { status: 500 })
        }),
      )
      const result = await updateWatchStatus('act-1', 'SomeDrama', 'watching')
      expect(result).toBe(false)
    })
  })

  describe('updateTier', () => {
    it('returns true on success', async () => {
      const result = await updateTier('act-1', 's')
      expect(result).toBe(true)
    })
  })

  describe('deleteActress', () => {
    it('returns true on success', async () => {
      const result = await deleteActress('act-1')
      expect(result).toBe(true)
    })
  })

  describe('auth headers', () => {
    it('attaches Authorization header with token', async () => {
      let authHeader = ''
      server.use(
        http.get(`${BASE}/actresses`, ({ request }) => {
          authHeader = request.headers.get('Authorization') || ''
          return HttpResponse.json([])
        }),
      )
      await fetchActresses()
      expect(authHeader).toBe('Bearer test-token')
    })
  })
})
