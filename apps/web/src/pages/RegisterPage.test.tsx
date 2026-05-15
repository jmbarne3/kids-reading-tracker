import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import RegisterPage from './RegisterPage'

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

const mockRegister = vi.fn()
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
  return { user: null, loading: false, login: vi.fn(), logout: vi.fn(), register: mockRegister }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/first name/i), 'Alice')
  await user.type(screen.getByLabelText(/last name/i), 'Smith')
  await user.type(screen.getByLabelText(/email address/i), 'alice@example.com')
  await user.type(screen.getByLabelText(/username/i), 'alice')
  await user.type(screen.getByLabelText(/^password/i), 'Password1!')
  await user.type(screen.getByLabelText(/confirm password/i), 'Password1!')
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAuth).mockReturnValue(unauthContext())
  })

  it('renders all required form fields and the submit button', () => {
    render(<MemoryRouter><RegisterPage /></MemoryRouter>)
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/last name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
  })

  it('shows a link to the login page', () => {
    render(<MemoryRouter><RegisterPage /></MemoryRouter>)
    expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument()
  })

  it('shows an error and does not call register when passwords do not match', async () => {
    const user = userEvent.setup()
    render(<MemoryRouter><RegisterPage /></MemoryRouter>)
    await user.type(screen.getByLabelText(/^password/i), 'Password1!')
    await user.type(screen.getByLabelText(/confirm password/i), 'Different2!')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(screen.getByRole('alert')).toHaveTextContent(/passwords do not match/i)
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('shows an error alert when the API rejects the registration', async () => {
    mockRegister.mockRejectedValue(new Error('Username already taken.'))
    const user = userEvent.setup()
    render(<MemoryRouter><RegisterPage /></MemoryRouter>)
    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Username already taken.'),
    )
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('calls register with form data and navigates to /library on success', async () => {
    mockRegister.mockResolvedValue(undefined)
    const user = userEvent.setup()
    render(<MemoryRouter><RegisterPage /></MemoryRouter>)
    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))
    await waitFor(() =>
      expect(mockRegister).toHaveBeenCalledWith(
        expect.objectContaining({
          email: 'alice@example.com',
          username: 'alice',
          first_name: 'Alice',
          last_name: 'Smith',
        }),
      ),
    )
    expect(mockNavigate).toHaveBeenCalledWith('/library', { replace: true })
  })

  it('disables the submit button while a submission is in-flight', async () => {
    let resolveRegister: () => void = () => {}
    mockRegister.mockReturnValue(new Promise<void>((resolve) => { resolveRegister = resolve }))
    const user = userEvent.setup()
    render(<MemoryRouter><RegisterPage /></MemoryRouter>)
    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(screen.getByRole('button', { name: /creating account/i })).toBeDisabled()
    resolveRegister()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /create account/i })).not.toBeDisabled(),
    )
  })
})
