import { describe, it, expect } from 'vitest'
import { TIERS, GENRES, TIER_MAP, TIER_COLOR, TIER_WEIGHT } from '../constants'

describe('constants', () => {
  describe('TIERS', () => {
    it('has 6 tier entries', () => {
      expect(TIERS).toHaveLength(6)
    })

    it('includes S+ tier as first entry', () => {
      expect(TIERS[0]).toEqual({
        id: 'splus',
        label: 'S+',
        color: '#E500A4',
        desc: 'Legendary',
      })
    })

    it('includes all expected tier ids', () => {
      const ids = TIERS.map((t) => t.id)
      expect(ids).toEqual(['splus', 's', 'a', 'b', 'c', 'd'])
    })

    it('each tier has id, label, color, and desc', () => {
      for (const tier of TIERS) {
        expect(tier).toHaveProperty('id')
        expect(tier).toHaveProperty('label')
        expect(tier).toHaveProperty('color')
        expect(tier).toHaveProperty('desc')
        expect(tier.color).toMatch(/^#[0-9A-Fa-f]{6}$/)
      }
    })
  })

  describe('GENRES', () => {
    it('has expected number of genres', () => {
      expect(GENRES.length).toBeGreaterThanOrEqual(8)
    })

    it('starts with "All"', () => {
      expect(GENRES[0]).toBe('All')
    })

    it('includes Romance, Fantasy, Thriller, Comedy', () => {
      expect(GENRES).toContain('Romance')
      expect(GENRES).toContain('Fantasy')
      expect(GENRES).toContain('Thriller')
      expect(GENRES).toContain('Comedy')
    })

    it('includes Action, Horror, Historical, Drama', () => {
      expect(GENRES).toContain('Action')
      expect(GENRES).toContain('Horror')
      expect(GENRES).toContain('Historical')
      expect(GENRES).toContain('Drama')
    })
  })

  describe('TIER_MAP', () => {
    it('maps tier ids to their definitions', () => {
      expect(TIER_MAP['s']).toEqual({
        id: 's',
        label: 'S',
        color: '#FF2942',
        desc: 'Outstanding',
      })
    })

    it('has entries for all tier ids', () => {
      for (const tier of TIERS) {
        expect(TIER_MAP[tier.id]).toEqual(tier)
      }
    })
  })

  describe('TIER_COLOR', () => {
    it('maps tier ids to color strings', () => {
      expect(TIER_COLOR['splus']).toBe('#E500A4')
      expect(TIER_COLOR['s']).toBe('#FF2942')
      expect(TIER_COLOR['a']).toBe('#FF7B3A')
    })
  })

  describe('TIER_WEIGHT', () => {
    it('assigns highest weight to splus', () => {
      expect(TIER_WEIGHT['splus']).toBe(6)
    })

    it('assigns lowest weight to d', () => {
      expect(TIER_WEIGHT['d']).toBe(1)
    })

    it('weights decrease from splus to d', () => {
      expect(TIER_WEIGHT['splus']).toBeGreaterThan(TIER_WEIGHT['s'])
      expect(TIER_WEIGHT['s']).toBeGreaterThan(TIER_WEIGHT['a'])
      expect(TIER_WEIGHT['a']).toBeGreaterThan(TIER_WEIGHT['b'])
      expect(TIER_WEIGHT['b']).toBeGreaterThan(TIER_WEIGHT['c'])
      expect(TIER_WEIGHT['c']).toBeGreaterThan(TIER_WEIGHT['d'])
    })
  })
})
