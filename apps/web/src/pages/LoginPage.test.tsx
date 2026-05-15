import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import LoginPage from './LoginPage'

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

const mockLogin = vi.fn()
const mockNavigate = vi.fn()

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('react-router-dom', async (importOriginal) => {
  const mod = await importOriginal<typeof import('react-router-dom')>()
  return { ...mod, useNavigate: () => mockNavigate }
})

import { useAuth } from '../context/AuthContext'

function unauthContext() {
  return { user: null, loading: false, login: mockLogin, logout: vi.fn(), register: vi.fn() }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAuth).mockReturnValue(unauthContext())
  })

  it('renders email, password fields and submit button', () => {
    render(<MemoryRouter><LoginPage /></MemoryRouter>)
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument()
  })

  it('shows an error alert when login fails', async () => {
    mockLogin.mockRejectedValue(new Error('Invalid credentials'))
    render(<MemoryRouter><LoginPage /></MemoryRouter>)
    await userEvent.type(screen.getByLabelText(/email address/i), 'bad@example.com')
    await userEvent.type(screen.getByLabelText(/^password/i), 'wrongpass')
    await userEvent.click(screen.getByRole('button', { name: 'Sign In' }))
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Invalid credentials'),
    )
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('calls login with form values and navigates on success', async () => {
    mockLogin.mockResolvedValue(undefined)
    render(<MemoryRouter><LoginPage /></MemoryRouter>)
    await userEvent.type(screen.getByLabelText(/email address/i), 'alice@example.com')
    await userEvent.type(screen.getByLabelText(/^password/i), 'password123')
    await userEvent.click(screen.getByRole('button', { name: 'Sign In' }))
    await waitFor(() =>
      expect(mockLogin).toHaveBeenCalledWith('alice@example.com', 'password123'),
    )
    expect(mockNavigate).toHaveBeenCalled()
  })

  it('disables the submit button while a submission is in-flight', async () => {
    let resolveLogin: () => void = () => {}
    mockLogin.mockReturnValue(new Promise<void>((resolve) => { resolveLogin = resolve }))
    render(<MemoryRouter><LoginPage /></MemoryRouter>)
    await userEvent.type(screen.getByLabelText(/email address/i), 'alice@example.com')
    await userEvent.type(screen.getByLabelText(/^password/i), 'password123')
    await userEvent.click(screen.getByRole('button', { name: 'Sign In' }))
    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
    resolveLogin()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Sign In' })).not.toBeDisabled(),
    )
  })

  it('shows a link to the register page', () => {
    render(<MemoryRouter><LoginPage /></MemoryRouter>)
    expect(screen.getByRole('link', { name: /create one/i })).toBeInTheDocument()
  })
})
