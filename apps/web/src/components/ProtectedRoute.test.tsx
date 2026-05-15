import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
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

function authContext(user: User | null, loading = false) {
  return { user, loading, login: vi.fn(), logout: vi.fn(), register: vi.fn() }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ProtectedRoute', () => {
  it('shows a loading spinner while auth state is resolving', () => {
    vi.mocked(useAuth).mockReturnValue(authContext(null, true))
    render(
      <MemoryRouter initialEntries={['/library']}>
        <ProtectedRoute><p>children</p></ProtectedRoute>
      </MemoryRouter>,
    )
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByText('children')).not.toBeInTheDocument()
  })

  it('redirects to /login when the user is not authenticated', () => {
    vi.mocked(useAuth).mockReturnValue(authContext(null, false))
    render(
      <MemoryRouter initialEntries={['/library']}>
        <Routes>
          <Route path="/login" element={<p>login page</p>} />
          <Route
            path="/library"
            element={
              <ProtectedRoute>
                <p>protected content</p>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('login page')).toBeInTheDocument()
    expect(screen.queryByText('protected content')).not.toBeInTheDocument()
  })

  it('renders children when the user is authenticated', () => {
    vi.mocked(useAuth).mockReturnValue(authContext(mockUser, false))
    render(
      <MemoryRouter>
        <ProtectedRoute><p>protected content</p></ProtectedRoute>
      </MemoryRouter>,
    )
    expect(screen.getByText('protected content')).toBeInTheDocument()
  })
})
