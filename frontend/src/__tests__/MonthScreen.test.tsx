// @vitest-environment jsdom
// Step 5: the Month screen. Spec 'Frontend' -> MonthScreen. Data is the real
// /api/month answer at 09:20 (fixtures/month-0920.json).
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MonthScreen } from '../screens/MonthScreen'
import month from './fixtures/month-0920.json'

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn(async (url: string) => {
    const cutoff = new URLSearchParams(url.split('?')[1]).get('cutoff')!
    return { ok: true, status: 200, json: async () => ({ ...month, cutoff }) }
  })
  vi.stubGlobal('fetch', fetchMock)
  window.history.pushState({}, '', '/month?cutoff=09:20')
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('MonthScreen', () => {
  it('shows Loading… before the reply arrives', () => {
    render(<MonthScreen />)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })

  it('asks the API for the month at the cutoff in the address bar', async () => {
    render(<MonthScreen />)
    await screen.findByTestId('tile-mae')
    expect(fetchMock).toHaveBeenCalledWith('/api/month?cutoff=09:20')
  })

  it('shows the four headline tiles', async () => {
    render(<MonthScreen />)
    expect(await screen.findByTestId('tile-mae')).toHaveTextContent('2,038.9 MW')
    expect(screen.getByTestId('tile-bias')).toHaveTextContent('+1,747.9 MW')
    expect(screen.getByTestId('tile-too-high')).toHaveTextContent('632 of 744 (85%)')
    expect(screen.getByTestId('tile-p90')).toHaveTextContent('4,098.5 MW')
  })

  it('says how often the miss was 1,000 MW or more', async () => {
    render(<MonthScreen />)
    expect(await screen.findByText(/552 of 744 hours/)).toBeInTheDocument()
  })

  it('draws one bar per hour of day', async () => {
    render(<MonthScreen />)
    expect(await screen.findAllByTestId('hod-bar')).toHaveLength(24)
  })

  it('the chart has MW numbers on its side axis and scales to its box', async () => {
    const { container } = render(<MonthScreen />)
    await screen.findAllByTestId('hod-bar')
    const svg = container.querySelector('svg')!
    const labels = [...svg.querySelectorAll('text')].map((t) => t.textContent ?? '')
    expect(labels.some((l) => /^\d{1,2},\d{3}$/.test(l))).toBe(true)
    expect(labels.some((l) => l.includes('MW'))).toBe(true)
    expect(svg.getAttribute('viewBox')).toBeTruthy()
    expect(['100%', null]).toContain(svg.getAttribute('width'))
  })

  it('lists the 3 worst then the 3 best days, worst first', async () => {
    render(<MonthScreen />)
    const rows = await screen.findAllByTestId('day-row')
    expect(rows).toHaveLength(6)
    expect(rows[0]).toHaveTextContent('28 Jan')
    expect(rows[1]).toHaveTextContent('12 Jan')
    expect(rows[2]).toHaveTextContent('11 Jan')
    expect(rows.slice(3).some((r) => r.textContent!.includes('19 Jan'))).toBe(true)
  })

  it('links each day row to that day on the Day screen', async () => {
    render(<MonthScreen />)
    const rows = await screen.findAllByTestId('day-row')
    const link = rows[0].querySelector('a')!
    expect(link).toHaveAttribute('href', '/?date=2026-01-28&cutoff=09:20')
  })

  it('the 09:50 switch refetches the month', async () => {
    render(<MonthScreen />)
    await screen.findByTestId('tile-mae')
    fireEvent.click(screen.getByRole('button', { name: '09:50 N2EX' }))
    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith('/api/month?cutoff=09:50'))
    expect(window.location.search).toContain('cutoff=09:50')
  })

  it('explains how to read the numbers', async () => {
    render(<MonthScreen />)
    await screen.findByTestId('tile-mae')
    expect(screen.getByText(/forecast − actual/)).toBeInTheDocument()
  })

  // The browser Back button must move the screen with the address bar.
  it('Back after the 09:50 switch returns the month to 09:20', async () => {
    render(<MonthScreen />)
    await screen.findByTestId('tile-mae')
    fireEvent.click(screen.getByRole('button', { name: '09:50 N2EX' }))
    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith('/api/month?cutoff=09:50'))
    window.history.back()
    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith('/api/month?cutoff=09:20'))
    expect(await screen.findByRole('button', { name: '09:20 EPEX' })).toHaveAttribute('aria-pressed', 'true')
  })
})
