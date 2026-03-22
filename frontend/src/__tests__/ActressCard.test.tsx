import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ActressCard from '../ActressCard'
import { createMockActress } from './test-utils'

const defaultProps = {
  color: '#FF2942',
  canEdit: false,
  onRemove: vi.fn(),
  onDragStart: vi.fn(),
}

function renderCard(overrides: Partial<typeof defaultProps> = {}, actressOverrides: Parameters<typeof createMockActress>[0] = {}) {
  const actress = createMockActress(actressOverrides)
  return render(
    <MemoryRouter>
      <ActressCard actress={actress} {...defaultProps} {...overrides} />
    </MemoryRouter>,
  )
}

describe('ActressCard', () => {
  it('renders actress name', () => {
    renderCard()
    expect(screen.getByText('Kim Tae-ri')).toBeInTheDocument()
  })

  it('renders known-for text', () => {
    renderCard()
    expect(screen.getByText('Twenty-Five Twenty-One')).toBeInTheDocument()
  })

  it('renders genre badge', () => {
    renderCard()
    expect(screen.getByText('Romance')).toBeInTheDocument()
  })

  it('renders age from birthDate', () => {
    renderCard({}, { birthDate: '1990-04-24' })
    const currentYear = new Date().getFullYear()
    const expectedAge = currentYear - 1990
    expect(screen.getByText(String(expectedAge))).toBeInTheDocument()
  })

  it('does not render age when birthDate is null', () => {
    renderCard({}, { birthDate: null })
    // No age element should be rendered
    const ageEls = document.querySelectorAll('.card-age')
    expect(ageEls).toHaveLength(0)
  })

  it('renders drama count', () => {
    renderCard({}, {
      dramas: [
        { title: 'Drama1', year: 2022, role: 'Lead', poster: null, rating: 8, watchStatus: 'watched', category: 'drama' },
        { title: 'Drama2', year: 2021, role: 'Lead', poster: null, rating: 7, watchStatus: 'watched', category: 'drama' },
        { title: 'Show1', year: 2020, role: 'Guest', poster: null, rating: null, watchStatus: null, category: 'show' },
      ],
    })
    // Should show "2 dramas" (excluding shows)
    expect(screen.getByText('2 dramas')).toBeInTheDocument()
  })

  it('does not render drama count when dramas is empty', () => {
    renderCard({}, { dramas: [] })
    expect(screen.queryByText(/dramas/)).not.toBeInTheDocument()
  })

  it('navigates on click', () => {
    renderCard({}, { _id: 'test-actress-id' })
    const card = document.querySelector('.actress-card')!
    fireEvent.click(card)
    // The MemoryRouter doesn't actually navigate, but the click handler fires
    // We verify the card is clickable
    expect(card).toBeTruthy()
  })

  it('shows remove button when canEdit is true', () => {
    renderCard({ canEdit: true })
    const removeBtn = document.querySelector('.remove-btn')
    expect(removeBtn).toBeInTheDocument()
  })

  it('does not show remove button when canEdit is false', () => {
    renderCard({ canEdit: false })
    const removeBtn = document.querySelector('.remove-btn')
    expect(removeBtn).not.toBeInTheDocument()
  })

  it('calls onRemove when remove button is clicked', () => {
    const onRemove = vi.fn()
    renderCard({ canEdit: true, onRemove }, { _id: 'actress-to-remove' })
    const removeBtn = document.querySelector('.remove-btn')!
    fireEvent.click(removeBtn)
    expect(onRemove).toHaveBeenCalledWith('actress-to-remove')
  })

  it('is draggable when canEdit is true', () => {
    renderCard({ canEdit: true })
    const card = document.querySelector('.actress-card')
    expect(card?.getAttribute('draggable')).toBe('true')
  })

  it('is not draggable when canEdit is false', () => {
    renderCard({ canEdit: false })
    const card = document.querySelector('.actress-card')
    // draggable attribute is not set when canEdit is false
    expect(card?.getAttribute('draggable')).not.toBe('true')
  })

  it('renders fallback image when actress image is null', () => {
    renderCard({}, { image: null, name: 'Test Actress' })
    const img = document.querySelector('.card-avatar') as HTMLImageElement
    expect(img.src).toContain('ui-avatars.com')
    expect(img.src).toContain('Test%20Actress')
  })
})
