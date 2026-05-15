import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import HomePage from './HomePage'
import type { User } from '../api/auth'

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from '../context/AuthContext'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockUser: User = {
  id: 1,
  username: 'alice',
  email: 'alice@example.com',
  first_name: 'Alice',
  last_name: 'Smith',
  role: 'parent',
  date_of_birth: null,
  avatar_url: '',
}

function authContext(user: User | null) {
  return { user, loading: false, login: vi.fn(), logout: vi.fn(), register: vi.fn() }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('HomePage', () => {
  it('renders the hero heading', () => {
    vi.mocked(useAuth).mockReturnValue(authContext(null))
    render(<MemoryRouter><HomePage /></MemoryRouter>)
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
  })

  it('shows a "Get Started" CTA when not authenticated', () => {
    vi.mocked(useAuth).mockReturnValue(authContext(null))
    render(<MemoryRouter><HomePage /></MemoryRouter>)
    expect(screen.getByRole('link', { name: /get started/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /go to my library/i })).not.toBeInTheDocument()
  })

  it('shows a "Go to My Library" CTA when authenticated', () => {
    vi.mocked(useAuth).mockReturnValue(authContext(mockUser))
    render(<MemoryRouter><HomePage /></MemoryRouter>)
    expect(screen.getByRole('link', { name: /go to my library/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /get started/i })).not.toBeInTheDocument()
  })

  it('renders the feature section headings', () => {
    vi.mocked(useAuth).mockReturnValue(authContext(null))
    render(<MemoryRouter><HomePage /></MemoryRouter>)
    expect(screen.getByText(/build bookshelves/i)).toBeInTheDocument()
    expect(screen.getByText(/track progress/i)).toBeInTheDocument()
  })
})
