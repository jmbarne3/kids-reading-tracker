import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import LibraryPage from './LibraryPage'
import type { ShelfEntry } from '../api/library'
import type { User } from '../api/auth'

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('../api/library', () => ({
  getShelf: vi.fn(),
  addBookByISBN: vi.fn(),
  moveToShelf: vi.fn(),
  removeFromShelf: vi.fn(),
  SHELF_LABELS: {
    currently_reading: 'Currently Reading',
    want_to_read: 'Want to Read',
    read: 'Read',
    did_not_finish: 'Did Not Finish',
  },
}))

import { useAuth } from '../context/AuthContext'
import { getShelf, removeFromShelf, moveToShelf } from '../api/library'

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

function authContext(user: User | null = mockUser) {
  return { user, loading: false, login: vi.fn(), logout: vi.fn(), register: vi.fn() }
}

function makeEntry(overrides: Partial<ShelfEntry> = {}): ShelfEntry {
  return {
    id: 1,
    shelf: 'currently_reading',
    added_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    book: {
      id: 1,
      title: 'Harry Potter',
      author_names: ['J.K. Rowling'],
      isbn_13: '9780747532699',
      cover_image_url: '',
      page_count: 309,
    },
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('LibraryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAuth).mockReturnValue(authContext())
  })

  it('renders all four shelf tabs', async () => {
    vi.mocked(getShelf).mockResolvedValue([])
    render(<MemoryRouter><LibraryPage /></MemoryRouter>)
    expect(screen.getByRole('button', { name: /currently reading/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /want to read/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^read$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /did not finish/i })).toBeInTheDocument()
  })

  it('shows a loading spinner while fetching the shelf', () => {
    vi.mocked(getShelf).mockReturnValue(new Promise(() => {}))
    render(<MemoryRouter><LibraryPage /></MemoryRouter>)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('shows empty-state message when the shelf has no books', async () => {
    vi.mocked(getShelf).mockResolvedValue([])
    render(<MemoryRouter><LibraryPage /></MemoryRouter>)
    await waitFor(() =>
      expect(screen.getByText(/no books here yet/i)).toBeInTheDocument(),
    )
  })

  it('renders book cards when the shelf has entries', async () => {
    vi.mocked(getShelf).mockResolvedValue([makeEntry()])
    render(<MemoryRouter><LibraryPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Harry Potter')).toBeInTheDocument())
    expect(screen.getByText('J.K. Rowling')).toBeInTheDocument()
    expect(screen.getByText('309 pages')).toBeInTheDocument()
  })

  it('shows the personalised welcome message', async () => {
    vi.mocked(getShelf).mockResolvedValue([])
    render(<MemoryRouter><LibraryPage /></MemoryRouter>)
    await waitFor(() =>
      expect(screen.getByText(/welcome back, alice/i)).toBeInTheDocument(),
    )
  })

  it('removes a book when the Remove button is clicked', async () => {
    vi.mocked(getShelf).mockResolvedValue([makeEntry()])
    vi.mocked(removeFromShelf).mockResolvedValue(undefined)
    render(<MemoryRouter><LibraryPage /></MemoryRouter>)
    await waitFor(() => screen.getByText('Harry Potter'))
    await userEvent.click(screen.getByRole('button', { name: /remove/i }))
    expect(removeFromShelf).toHaveBeenCalledWith(1)
    await waitFor(() =>
      expect(screen.queryByText('Harry Potter')).not.toBeInTheDocument(),
    )
  })

  it('fetches the correct shelf when a tab is clicked', async () => {
    vi.mocked(getShelf).mockResolvedValue([])
    render(<MemoryRouter><LibraryPage /></MemoryRouter>)
    await waitFor(() => screen.getByText(/no books here yet/i))
    await userEvent.click(screen.getByRole('button', { name: /want to read/i }))
    expect(getShelf).toHaveBeenCalledWith('want_to_read')
  })

  it('moves a book to another shelf and removes it from the current view', async () => {
    const entry = makeEntry({ id: 42, shelf: 'currently_reading' })
    const moved = makeEntry({ id: 42, shelf: 'read' })
    vi.mocked(getShelf).mockResolvedValue([entry])
    vi.mocked(moveToShelf).mockResolvedValue(moved)
    render(<MemoryRouter><LibraryPage /></MemoryRouter>)
    await waitFor(() => screen.getByText('Harry Potter'))
    // Click the 'Read' option inside the dropdown menu (hidden by Bootstrap CSS)
    const dropdownMenu = document.querySelector('.dropdown-menu')!
    await userEvent.click(within(dropdownMenu as HTMLElement).getByText('Read'))
    expect(moveToShelf).toHaveBeenCalledWith(42, 'read')
    await waitFor(() =>
      expect(screen.queryByText('Harry Potter')).not.toBeInTheDocument(),
    )
  })
})
