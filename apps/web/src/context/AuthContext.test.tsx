import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider, useAuth } from './AuthContext'
import type { User } from '../api/auth'

// Auto-mock the entire auth API module so no real HTTP calls are made.
vi.mock('../api/auth')

import { getMe, login as apiLogin, logout as apiLogout } from '../api/auth'

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

// A minimal consumer that exposes auth state for assertions.
function AuthStateDisplay() {
  const { user, loading } = useAuth()
  if (loading) return <p>loading</p>
  return <p>{user ? `signed-in:${user.email}` : 'signed-out'}</p>
}

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading while getMe is in-flight', () => {
    vi.mocked(getMe).mockReturnValue(new Promise(() => {})) // never resolves
    renderWithRouter(
      <AuthProvider>
        <AuthStateDisplay />
      </AuthProvider>,
    )
    expect(screen.getByText('loading')).toBeInTheDocument()
  })

  it('resolves to signed-out when no session exists', async () => {
    vi.mocked(getMe).mockResolvedValue(null)
    renderWithRouter(
      <AuthProvider>
        <AuthStateDisplay />
      </AuthProvider>,
    )
    await waitFor(() => expect(screen.getByText('signed-out')).toBeInTheDocument())
  })

  it('resolves to signed-in when a session exists', async () => {
    vi.mocked(getMe).mockResolvedValue(mockUser)
    renderWithRouter(
      <AuthProvider>
        <AuthStateDisplay />
      </AuthProvider>,
    )
    await waitFor(() =>
      expect(screen.getByText('signed-in:alice@example.com')).toBeInTheDocument(),
    )
  })

  it('login() updates user state', async () => {
    vi.mocked(getMe).mockResolvedValue(null)
    vi.mocked(apiLogin).mockResolvedValue(mockUser)

    function LoginTrigger() {
      const { login } = useAuth()
      return <button onClick={() => login('alice@example.com', 'pass')}>do-login</button>
    }

    renderWithRouter(
      <AuthProvider>
        <AuthStateDisplay />
        <LoginTrigger />
      </AuthProvider>,
    )

    await waitFor(() => screen.getByText('signed-out'))
    await userEvent.click(screen.getByRole('button', { name: 'do-login' }))
    await waitFor(() =>
      expect(screen.getByText('signed-in:alice@example.com')).toBeInTheDocument(),
    )
  })

  it('logout() clears user state', async () => {
    vi.mocked(getMe).mockResolvedValue(mockUser)
    vi.mocked(apiLogout).mockResolvedValue(undefined)

    function LogoutTrigger() {
      const { logout } = useAuth()
      return <button onClick={() => logout()}>do-logout</button>
    }

    renderWithRouter(
      <AuthProvider>
        <AuthStateDisplay />
        <LogoutTrigger />
      </AuthProvider>,
    )

    await waitFor(() => screen.getByText('signed-in:alice@example.com'))
    await userEvent.click(screen.getByRole('button', { name: 'do-logout' }))
    await waitFor(() => expect(screen.getByText('signed-out')).toBeInTheDocument())
  })

  it('useAuth throws when used outside AuthProvider', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<AuthStateDisplay />)).toThrow(
      'useAuth must be used inside AuthProvider',
    )
    consoleSpy.mockRestore()
  })
})
