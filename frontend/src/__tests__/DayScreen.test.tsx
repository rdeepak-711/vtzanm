// @vitest-environment jsdom
// Step 5: the Day screen. Spec 'Frontend' -> DayScreen. Data is the real
// /api/day answer for 15 Jan (fixtures/day-2026-01-15.json).
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DayScreen } from '../screens/DayScreen'
import day15 from './fixtures/day-2026-01-15.json'

function dayReply(date: string, cutoff: string) {
  return { ...day15, date, cutoff }
}

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn(async (url: string) => {
    const q = new URLSearchParams(url.split('?')[1])
    return { ok: true, status: 200, json: async () => dayReply(q.get('date')!, q.get('cutoff')!) }
  })
  vi.stubGlobal('fetch', fetchMock)
  window.history.pushState({}, '', '/?date=2026-01-15&cutoff=09:20')
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('DayScreen', () => {
  it('shows Loading… before the reply arrives', () => {
    render(<DayScreen />)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })

  it('asks the API for the day in the address bar', async () => {
    render(<DayScreen />)
    await screen.findAllByTestId('hour-row')
    expect(fetchMock).toHaveBeenCalledWith('/api/day?date=2026-01-15&cutoff=09:20')
  })

  it('defaults to 15 Jan at 09:20 when the address has no date', async () => {
    window.history.pushState({}, '', '/')
    render(<DayScreen />)
    await screen.findAllByTestId('hour-row')
    expect(fetchMock).toHaveBeenCalledWith('/api/day?date=2026-01-15&cutoff=09:20')
  })

  it('shows one row per hour', async () => {
    render(<DayScreen />)
    expect(await screen.findAllByTestId('hour-row')).toHaveLength(24)
  })

  it('shows forecast, actual and signed miss for 12:00', async () => {
    render(<DayScreen />)
    const row = (await screen.findAllByTestId('hour-row'))[12]
    expect(row).toHaveTextContent('11,049 MW')
    expect(row).toHaveTextContent('9,790.5 MW')
    expect(row).toHaveTextContent('+1,258.5 MW')
  })

  it('shows the report card for the day', async () => {
    render(<DayScreen />)
    expect(await screen.findByTestId('summary-mae')).toHaveTextContent('1,041.8 MW')
    expect(screen.getByTestId('summary-bias')).toHaveTextContent('+1,041.8 MW')
    expect(screen.getByTestId('summary-too_high')).toHaveTextContent('24 of 24')
    expect(screen.getByTestId('summary-p90')).toHaveTextContent('1,633.5 MW')
  })

  it('says which forecast run was used, in UTC', async () => {
    render(<DayScreen />)
    expect(await screen.findByText(/Forecast run used:/)).toHaveTextContent('14 Jan 07:30')
  })

  it('draws a chart', async () => {
    const { container } = render(<DayScreen />)
    await screen.findAllByTestId('hour-row')
    expect(container.querySelector('svg')).not.toBeNull()
  })

  it('the chart has MW numbers on its side axis', async () => {
    const { container } = render(<DayScreen />)
    await screen.findAllByTestId('hour-row')
    const svg = container.querySelector('svg')!
    const labels = [...svg.querySelectorAll('text')].map((t) => t.textContent ?? '')
    expect(labels.some((l) => /^\d{1,2},\d{3}$/.test(l))).toBe(true)
    expect(labels.some((l) => l.includes('MW'))).toBe(true)
  })

  it('the chart scales to its box instead of a fixed width', async () => {
    const { container } = render(<DayScreen />)
    await screen.findAllByTestId('hour-row')
    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('viewBox')).toBeTruthy()
    expect(['100%', null]).toContain(svg.getAttribute('width'))
  })

  it('Next day asks for 16 Jan and updates the address', async () => {
    render(<DayScreen />)
    await screen.findAllByTestId('hour-row')
    fireEvent.click(screen.getByRole('button', { name: 'Next day' }))
    await waitFor(() =>
      expect(fetchMock).toHaveBeenLastCalledWith('/api/day?date=2026-01-16&cutoff=09:20'),
    )
    expect(window.location.search).toContain('date=2026-01-16')
  })

  it('Previous day is disabled on the first day, Next day on the last', async () => {
    window.history.pushState({}, '', '/?date=2026-01-02&cutoff=09:20')
    render(<DayScreen />)
    await screen.findAllByTestId('hour-row')
    expect(screen.getByRole('button', { name: 'Previous day' })).toBeDisabled()
    cleanup()

    window.history.pushState({}, '', '/?date=2026-02-01&cutoff=09:20')
    render(<DayScreen />)
    await screen.findAllByTestId('hour-row')
    expect(screen.getByRole('button', { name: 'Next day' })).toBeDisabled()
  })

  it('limits the date picker to the January window', async () => {
    const { container } = render(<DayScreen />)
    await screen.findAllByTestId('hour-row')
    const input = container.querySelector('input[type="date"]')!
    expect(input).toHaveAttribute('min', '2026-01-02')
    expect(input).toHaveAttribute('max', '2026-02-01')
  })

  it('the 09:50 switch refetches and is marked pressed', async () => {
    render(<DayScreen />)
    await screen.findAllByTestId('hour-row')
    const n2ex = screen.getByRole('button', { name: '09:50 N2EX' })
    fireEvent.click(n2ex)
    await waitFor(() =>
      expect(fetchMock).toHaveBeenLastCalledWith('/api/day?date=2026-01-15&cutoff=09:50'),
    )
    expect(n2ex).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: '09:20 EPEX' })).toHaveAttribute('aria-pressed', 'false')
    expect(window.location.search).toContain('cutoff=09:50')
  })

  it("shows the server's message when the request fails", async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: false, status: 400, json: async () => ({ detail: 'allowed range 2026-01-02 to 2026-02-01' }),
    })))
    render(<DayScreen />)
    expect(await screen.findByRole('alert')).toHaveTextContent('allowed range 2026-01-02 to 2026-02-01')
  })

  it('a missing value leaves a gap in the chart line instead of dropping to zero', async () => {
    const hours = day15.hours.map((h, i) => (i === 5 ? { ...h, forecast_mw: null, error_mw: null } : h))
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ ...day15, hours }) })))
    const { container } = render(<DayScreen />)
    await screen.findAllByTestId('hour-row')
    const pts = [...container.querySelectorAll('.line-forecast')]
      .flatMap((el) => (el.getAttribute('points') ?? '').trim().split(/\s+/).filter(Boolean))
    expect(pts).toHaveLength(23)
  })

  it('marks a partial hour', async () => {
    const hours = day15.hours.map((h, i) => (i === 5 ? { ...h, partial: true } : h))
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ ...day15, hours }) })))
    render(<DayScreen />)
    const rows = await screen.findAllByTestId('hour-row')
    expect(within(rows[5]).getByText(/partial/i)).toBeInTheDocument()
    expect(within(rows[6]).queryByText(/partial/i)).toBeNull()
  })

  // Step 7: the browser Back button must move the screen with the address bar.
  it('Back after Next day returns the screen to 15 Jan', async () => {
    render(<DayScreen />)
    await screen.findAllByTestId('hour-row')
    fireEvent.click(screen.getByRole('button', { name: 'Next day' }))
    await waitFor(() =>
      expect(fetchMock).toHaveBeenLastCalledWith('/api/day?date=2026-01-16&cutoff=09:20'),
    )
    window.history.back()
    await waitFor(() =>
      expect(fetchMock).toHaveBeenLastCalledWith('/api/day?date=2026-01-15&cutoff=09:20'),
    )
    expect(screen.getByLabelText('Delivery date')).toHaveValue('2026-01-15')
  })

  it('Back after the 09:50 switch returns to 09:20', async () => {
    render(<DayScreen />)
    await screen.findAllByTestId('hour-row')
    fireEvent.click(screen.getByRole('button', { name: '09:50 N2EX' }))
    await waitFor(() =>
      expect(fetchMock).toHaveBeenLastCalledWith('/api/day?date=2026-01-15&cutoff=09:50'),
    )
    window.history.back()
    await waitFor(() =>
      expect(fetchMock).toHaveBeenLastCalledWith('/api/day?date=2026-01-15&cutoff=09:20'),
    )
    expect(await screen.findByRole('button', { name: '09:20 EPEX' })).toHaveAttribute('aria-pressed', 'true')
  })
})
