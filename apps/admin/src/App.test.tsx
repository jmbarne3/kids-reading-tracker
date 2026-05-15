import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

// The admin App.tsx is currently the Vite scaffold placeholder.
// These tests will grow as the admin dashboard is built out.

describe('App', () => {
  it('renders the Get started heading', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /get started/i })).toBeInTheDocument()
  })

  it('increments the counter when the button is clicked', async () => {
    render(<App />)
    const button = screen.getByRole('button', { name: /count is 0/i })
    expect(button).toBeInTheDocument()
    await userEvent.click(button)
    expect(screen.getByRole('button', { name: /count is 1/i })).toBeInTheDocument()
  })

  it('renders the Vite and React documentation links', () => {
    render(<App />)
    expect(screen.getByRole('link', { name: /explore vite/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /learn more/i })).toBeInTheDocument()
  })
})
