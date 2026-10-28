// Step 5: number and time formatting. Spec 'Frontend' -> format.ts.
import { describe, expect, it } from 'vitest'
import { fmtMw, fmtPct, fmtRun, fmtSigned } from '../format'

describe('fmtMw', () => {
  it('groups thousands and adds the unit', () => {
    expect(fmtMw(15834)).toBe('15,834 MW')
  })
  it('keeps one decimal when there is one', () => {
    expect(fmtMw(9790.5)).toBe('9,790.5 MW')
  })
  it('shows a dash for a missing value', () => {
    expect(fmtMw(null)).toBe('—')
  })
})

describe('fmtSigned', () => {
  it('puts a plus on positive misses (forecast too high)', () => {
    expect(fmtSigned(1377.5)).toBe('+1,377.5 MW')
  })
  it('uses a real minus sign on negative misses', () => {
    expect(fmtSigned(-605.5)).toBe('−605.5 MW')
  })
  it('shows zero without a sign', () => {
    expect(fmtSigned(0)).toBe('0 MW')
  })
  it('shows a dash for a missing value', () => {
    expect(fmtSigned(null)).toBe('—')
  })
})

describe('fmtRun', () => {
  it('shows the run time in UTC, not the browser zone', () => {
    // These tests run in India (UTC+5:30); local time would print 13:00.
    expect(fmtRun('2026-01-14T07:30:00Z')).toBe('14 Jan 07:30')
  })
  it('handles the month change', () => {
    expect(fmtRun('2026-01-31T07:30:00Z')).toBe('31 Jan 07:30')
  })
})

describe('fmtPct', () => {
  it('rounds a share to a whole percent', () => {
    expect(fmtPct(0.8494623655913979)).toBe('85%')
    expect(fmtPct(1)).toBe('100%')
  })
  it('shows a dash for a missing value', () => {
    expect(fmtPct(null)).toBe('—')
  })
})
