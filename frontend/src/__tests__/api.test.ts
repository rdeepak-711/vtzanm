// Step 5: the fetch wrappers. Spec 'Frontend' -> api.ts.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchDay, fetchMonth } from '../api'

function reply(status: number, body: unknown) {
  return vi.fn(async () => ({ ok: status === 200, status, json: async () => body }))
}

afterEach(() => vi.unstubAllGlobals())

describe('fetchDay', () => {
  it('calls /api/day with the date and cutoff and returns the body', async () => {
    const fetchMock = reply(200, { date: '2026-01-15' })
    vi.stubGlobal('fetch', fetchMock)
    const body = await fetchDay('2026-01-15', '09:20')
    expect(fetchMock).toHaveBeenCalledWith('/api/day?date=2026-01-15&cutoff=09:20')
    expect(body).toEqual({ date: '2026-01-15' })
  })

  it("throws the server's message on a 400", async () => {
    vi.stubGlobal('fetch', reply(400, { detail: 'allowed range 2026-01-02 to 2026-02-01' }))
    await expect(fetchDay('2026-01-01', '09:20')).rejects.toThrow('allowed range 2026-01-02 to 2026-02-01')
  })
})

describe('fetchMonth', () => {
  it('calls /api/month with the cutoff', async () => {
    const fetchMock = reply(200, { cutoff: '09:50' })
    vi.stubGlobal('fetch', fetchMock)
    await fetchMonth('09:50')
    expect(fetchMock).toHaveBeenCalledWith('/api/month?cutoff=09:50')
  })

  it("throws the server's message on a 400", async () => {
    vi.stubGlobal('fetch', reply(400, { detail: 'allowed cutoffs are 09:20 and 09:50' }))
    await expect(fetchMonth('10:00')).rejects.toThrow('allowed cutoffs are 09:20 and 09:50')
  })
})
