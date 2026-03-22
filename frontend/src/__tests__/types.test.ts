import { describe, it, expect } from 'vitest'
import type { WatchStatus, Drama, Actress, Tier, Stats, ChatMessage } from '../types'

describe('types', () => {
  describe('WatchStatus', () => {
    it('allows "watched" value', () => {
      const status: WatchStatus = 'watched'
      expect(status).toBe('watched')
    })

    it('allows "watching" value', () => {
      const status: WatchStatus = 'watching'
      expect(status).toBe('watching')
    })

    it('allows "plan_to_watch" value', () => {
      const status: WatchStatus = 'plan_to_watch'
      expect(status).toBe('plan_to_watch')
    })

    it('allows "dropped" value', () => {
      const status: WatchStatus = 'dropped'
      expect(status).toBe('dropped')
    })

    it('allows null value', () => {
      const status: WatchStatus = null
      expect(status).toBeNull()
    })
  })

  describe('Drama interface', () => {
    it('can create a valid Drama object', () => {
      const drama: Drama = {
        title: 'Crash Landing on You',
        year: 2019,
        role: 'Yoon Se-ri',
        poster: 'https://example.com/poster.jpg',
        rating: 9,
        watchStatus: 'watched',
        category: 'drama',
      }
      expect(drama.title).toBe('Crash Landing on You')
      expect(drama.year).toBe(2019)
      expect(drama.category).toBe('drama')
    })

    it('allows null poster and rating', () => {
      const drama: Drama = {
        title: 'Some Drama',
        year: 2023,
        role: 'Lead',
        poster: null,
        rating: null,
        watchStatus: null,
        category: 'show',
      }
      expect(drama.poster).toBeNull()
      expect(drama.rating).toBeNull()
      expect(drama.watchStatus).toBeNull()
    })
  })

  describe('Actress interface', () => {
    it('can create a valid Actress object', () => {
      const actress: Actress = {
        _id: '123',
        name: 'Kim Tae-ri',
        known: 'Twenty-Five Twenty-One',
        genre: 'Romance',
        year: 2022,
        tier: 's',
        image: null,
        birthDate: '1990-04-24',
        birthPlace: 'Seoul',
        agency: 'Management SOOP',
        dramas: [],
        awards: ['Best Actress'],
        gallery: [],
      }
      expect(actress._id).toBe('123')
      expect(actress.name).toBe('Kim Tae-ri')
      expect(actress.dramas).toEqual([])
    })

    it('allows nullable fields to be null', () => {
      const actress: Actress = {
        _id: '456',
        name: 'Test',
        known: 'Test Drama',
        genre: 'Action',
        year: 2023,
        tier: null,
        image: null,
        birthDate: null,
        birthPlace: null,
        agency: null,
        dramas: [],
        awards: [],
        gallery: [],
      }
      expect(actress.tier).toBeNull()
      expect(actress.image).toBeNull()
      expect(actress.birthDate).toBeNull()
      expect(actress.birthPlace).toBeNull()
      expect(actress.agency).toBeNull()
    })
  })

  describe('Tier interface', () => {
    it('has the expected shape', () => {
      const tier: Tier = { id: 's', label: 'S', color: '#FF2942' }
      expect(tier.id).toBe('s')
      expect(tier.label).toBe('S')
      expect(tier.color).toBe('#FF2942')
    })
  })

  describe('Stats interface', () => {
    it('has the expected shape', () => {
      const stats: Stats = {
        total: 10,
        ranked: 7,
        unranked: 3,
        genreCounts: { Romance: 5, Action: 2 },
        tierCounts: { s: 3, a: 4 },
      }
      expect(stats.total).toBe(10)
      expect(stats.genreCounts['Romance']).toBe(5)
    })
  })

  describe('ChatMessage interface', () => {
    it('can be a user message', () => {
      const msg: ChatMessage = { role: 'user', content: 'Hello' }
      expect(msg.role).toBe('user')
    })

    it('can be an assistant message', () => {
      const msg: ChatMessage = { role: 'assistant', content: 'Hi there' }
      expect(msg.role).toBe('assistant')
    })
  })
})
