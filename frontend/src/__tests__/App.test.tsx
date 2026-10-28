// @vitest-environment jsdom
// Step 5: which screen shows for which address, and the top bar.
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import day15 from './fixtures/day-2026-01-15.json'
import month from './fixtures/month-0920.json'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => ({
    ok: true, status: 200, json: async () => (url.startsWith('/api/month') ? month : day15),
  })))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('shows the Day screen at /', async () => {
    window.history.pushState({}, '', '/')
    render(<App />)
    expect(await screen.findAllByTestId('hour-row')).toHaveLength(24)
  })

  it('shows the Month screen at /month', async () => {
    window.history.pushState({}, '', '/month')
    render(<App />)
    expect(await screen.findByTestId('tile-mae')).toBeInTheDocument()
  })

  it('top bar links keep the cutoff', async () => {
    window.history.pushState({}, '', '/?cutoff=09:50')
    render(<App />)
    expect(screen.getByRole('link', { name: 'Day' })).toHaveAttribute('href', '/?cutoff=09:50')
    expect(screen.getByRole('link', { name: 'Month' })).toHaveAttribute('href', '/month?cutoff=09:50')
  })
})
