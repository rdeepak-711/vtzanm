const number = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1 })

export function fmtMw(n: number | null): string {
  return n === null ? '—' : n === 0 ? '0 MW' : `${number.format(n)} MW`
}

export function fmtSigned(n: number | null): string {
  if (n === null) return '—'
  if (n === 0) return '0 MW'
  return `${n > 0 ? '+' : '−'}${number.format(Math.abs(n))} MW`
}

export function fmtPct(share: number | null): string {
  return share === null ? '—' : `${Math.round(share * 100)}%`
}

export function fmtRun(iso: string): string {
  const date = new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    timeZone: 'UTC',
  }).format(new Date(iso))
  const time = new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone: 'UTC',
  }).format(new Date(iso))
  return `${date} ${time}`
}

export function fmtHour(iso: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone: 'UTC',
  }).format(new Date(iso))
}

export function fmtDate(iso: string, year = false): string {
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    ...(year ? { year: 'numeric' as const } : {}),
    timeZone: 'UTC',
  }).format(new Date(`${iso}T00:00:00Z`))
}
