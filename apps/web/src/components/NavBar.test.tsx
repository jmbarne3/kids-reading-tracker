import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import NavBar from './NavBar'
import type { User } from '../api/auth'

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

const mockLogout = vi.fn()
const mockNavigate = vi.fn()

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('react-router-dom', async (importOriginal) => {
  const mod = await importOriginal<typeof import('react-router-dom')>()
  return { ...mod, useNavigate: () => mockNavigate }
})

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
  return {
    user,
    loading: false,
    login: vi.fn(),
    logout: mockLogout,
    register: vi.fn(),
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('NavBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the brand link', () => {
    vi.mocked(useAuth).mockReturnValue(authContext(null))
    render(<MemoryRouter><NavBar /></MemoryRouter>)
    expect(screen.getByText(/Kids Reading Tracker/i)).toBeInTheDocument()
  })

  it('shows a Log In link when not authenticated', () => {
    vi.mocked(useAuth).mockReturnValue(authContext(null))
    render(<MemoryRouter><NavBar /></MemoryRouter>)
    expect(screen.getByRole('link', { name: /log in/i })).toBeInTheDocument()
    expect(screen.queryByText(/my library/i)).not.toBeInTheDocument()
  })

  it('shows My Library link and Log Out button when authenticated', () => {
    vi.mocked(useAuth).mockReturnValue(authContext(mockUser))
    render(<MemoryRouter><NavBar /></MemoryRouter>)
    expect(screen.getByRole('link', { name: /my library/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /log out/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /log in/i })).not.toBeInTheDocument()
  })

  it('calls logout and navigates to / when Log Out is clicked', async () => {
    mockLogout.mockResolvedValue(undefined)
    vi.mocked(useAuth).mockReturnValue(authContext(mockUser))
    render(<MemoryRouter><NavBar /></MemoryRouter>)
    await userEvent.click(screen.getByRole('button', { name: /log out/i }))
    expect(mockLogout).toHaveBeenCalledOnce()
    expect(mockNavigate).toHaveBeenCalledWith('/')
  })
})
