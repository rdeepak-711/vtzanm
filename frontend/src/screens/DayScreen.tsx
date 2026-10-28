import { useEffect, useState } from 'react'
import { fetchDay, type Cutoff, type DayResponse } from '../api'
import { fmtDate, fmtHour, fmtMw, fmtRun, fmtSigned } from '../format'
import { CutoffSwitch } from './CutoffSwitch'

const firstDay = '2026-01-02'
const lastDay = '2026-02-01'

// Reads the selected date and cutoff from the address bar.
function query() {
  const q = new URLSearchParams(window.location.search)
  return {
    date: q.get('date') || '2026-01-15',
    cutoff: (q.get('cutoff') === '09:50' ? '09:50' : '09:20') as Cutoff,
  }
}

// Writes the selected date and cutoff to the address bar.
function setQuery(date: string, cutoff: Cutoff) {
  window.history.pushState({}, '', `/?date=${date}&cutoff=${cutoff}`)
}

// Draws forecast and actual measurements as separate runs around missing hours.
function Lines({ data }: { data: DayResponse }) {
  const values = data.hours.flatMap((hour) =>
    [hour.forecast_mw, hour.actual_mw].filter((value): value is number => value !== null),
  )
  const min = values.length ? Math.min(...values) : 0
  const max = values.length ? Math.max(...values) : 1
  const span = max - min || 1
  const step = niceStep(span / 4)
  const firstTick = Math.floor(min / step) * step
  const lastTick = Math.ceil(max / step) * step
  const ticks = Array.from(
    { length: Math.max(2, Math.round((lastTick - firstTick) / step) + 1) },
    (_, index) => firstTick + index * step,
  )
  const axisMin = ticks[0]
  const axisMax = ticks[ticks.length - 1]
  const axisSpan = axisMax - axisMin || 1
  const y = (value: number) => 170 - ((value - axisMin) / axisSpan) * 145
  const plotLeft = 82
  const plotWidth = 554
  const series = ['forecast_mw', 'actual_mw'] as const

  // Returns one point string for each consecutive run with measured values.
  function points(key: (typeof series)[number]) {
    const runs: string[][] = []
    let currentRun: string[] = []
    data.hours.forEach((hour, index) => {
      const value = hour[key]
      if (value === null) {
        if (currentRun.length) runs.push(currentRun)
        currentRun = []
        return
      }
      const x = plotLeft + (index * plotWidth) / Math.max(1, data.hours.length - 1)
      currentRun.push(`${x},${y(value)}`)
    })
    if (currentRun.length) runs.push(currentRun)
    return runs.map((run) => run.join(' '))
  }

  return (
    <div className="chart-wrap">
      <svg
        className="day-chart"
        viewBox="0 0 660 205"
        role="img"
        aria-label="Forecast and actual wind by hour in UTC"
      >
        {ticks.map((value) => {
          const tickY = 170 - ((value - axisMin) / axisSpan) * 145
          return (
            <g key={value}>
              <line
                x1={plotLeft}
                x2={plotLeft + plotWidth}
                y1={tickY}
                y2={tickY}
                className="gridline"
              />
              <text x="72" y={tickY + 3} textAnchor="end">
                {Math.round(value).toLocaleString('en-GB')}
              </text>
            </g>
          )
        })}
        <text x="18" y="18" className="axis-title">
          MW
        </text>
        {points('forecast_mw').map((run, index) => (
          <polyline key={`forecast-${index}`} points={run} className="line-forecast" />
        ))}
        {points('actual_mw').map((run, index) => (
          <polyline key={`actual-${index}`} points={run} className="line-actual" />
        ))}
        {[0, 6, 12, 18, 23].map((hour) => (
          <text key={hour} x={plotLeft + (hour * plotWidth) / 23} y="198" textAnchor="middle">
            {String(hour).padStart(2, '0')}
          </text>
        ))}
      </svg>
    </div>
  )
}

// Chooses a readable tick interval for the chart axis.
function niceStep(value: number) {
  const magnitude = 10 ** Math.floor(Math.log10(Math.max(1, value)))
  const fraction = value / magnitude
  return (fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10) * magnitude
}

// Fetches the selected day and ignores results after the screen changes or unmounts.
function loadDay(
  date: string,
  cutoff: Cutoff,
  setData: (data: DayResponse | null) => void,
  setError: (error: string) => void,
) {
  let active = true
  setData(null)
  setError('')
  fetchDay(date, cutoff)
    .then((value) => {
      if (active) setData(value)
    })
    .catch((error: Error) => {
      if (active) setError(error.message)
    })
  return () => {
    active = false
  }
}

// Updates the browser address when a new date is selected.
function changeDate(value: string, cutoff: Cutoff, setDate: (date: string) => void) {
  if (!value) return
  setDate(value)
  setQuery(value, cutoff)
}

// Moves the selected date by the requested number of days.
function shiftDate(date: string, days: number, cutoff: Cutoff, setDate: (date: string) => void) {
  const nextDate = new Date(`${date}T00:00:00Z`)
  nextDate.setUTCDate(nextDate.getUTCDate() + days)
  changeDate(nextDate.toISOString().slice(0, 10), cutoff, setDate)
}

// Returns the style class for the signed-miss table cell.
function errorClass(error: number | null) {
  if (error === null || error === 0) return ''
  return error > 0 ? 'positive' : 'negative'
}

// Formats the minimum and maximum lead time used for a day's forecast.
function leadText(data: DayResponse) {
  if (!data.hours.length) return ''
  const leadHours = data.hours.map((hour) => hour.lead_hours)
  return `${Math.min(...leadHours)}–${Math.max(...leadHours)} h ahead`
}

// Shows the selected day's chart, summary, and hourly measurements.
export function DayScreen() {
  const initial = query()
  const [date, setDate] = useState(initial.date)
  const [cutoff, setCutoff] = useState(initial.cutoff)
  const [data, setData] = useState<DayResponse | null>(null)
  const [error, setError] = useState('')

  useEffect(() => loadDay(date, cutoff, setData, setError), [date, cutoff])

  // Restores the selected date and cutoff after browser navigation.
  function handlePopState() {
    const selected = query()
    setDate(selected.date)
    setCutoff(selected.cutoff)
  }

  useEffect(() => {
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  // Updates the cutoff and keeps the address bar in sync.
  function changeCutoff(value: Cutoff) {
    setCutoff(value)
    setQuery(date, value)
  }

  if (error) {
    return (
      <section className="content">
        <p role="alert">{error}</p>
      </section>
    )
  }
  if (!data) {
    return (
      <section className="content">
        <p>Loading…</p>
      </section>
    )
  }

  const runs = [...new Set(data.runs_used)]
  const lead = leadText(data)

  return (
    <section className="content">
      <div className="screen-heading">
        <div>
          <p className="eyebrow">DAILY REVIEW</p>
          <h1>{fmtDate(date, true)}</h1>
        </div>
        <CutoffSwitch cutoff={cutoff} onChange={changeCutoff} />
      </div>
      <div className="date-controls">
        <button
          aria-label="Previous day"
          disabled={date <= firstDay}
          onClick={() => shiftDate(date, -1, cutoff, setDate)}
        >
          ←
        </button>
        <input
          aria-label="Delivery date"
          type="date"
          min={firstDay}
          max={lastDay}
          value={date}
          onChange={(event) => changeDate(event.target.value, cutoff, setDate)}
        />
        <button
          aria-label="Next day"
          disabled={date >= lastDay}
          onClick={() => shiftDate(date, 1, cutoff, setDate)}
        >
          →
        </button>
      </div>
      <p className="decision">
        Decision time: {fmtDate(data.decision_time.slice(0, 10), true)}{' '}
        {fmtHour(data.decision_time)} · Forecast run used: {runs.map(fmtRun).join(', ')}
        {lead ? ` (${lead})` : ''}
      </p>
      <div className="panel">
        <Lines data={data} />
        <div className="legend">
          <span>
            <i className="key forecast" />
            Forecast
          </span>
          <span>
            <i className="key actual" />
            Actual
          </span>
        </div>
      </div>
      <div className="summary-grid">
        <article data-testid="summary-mae">
          <strong>{fmtMw(data.summary.mae_mw)}</strong>
          <span>Avg miss</span>
          <small>Average distance between forecast and actual.</small>
        </article>
        <article data-testid="summary-bias">
          <strong>{fmtSigned(data.summary.bias_mw)}</strong>
          <span>Lean</span>
          <small>+ means the forecast was higher than what arrived.</small>
        </article>
        <article data-testid="summary-too_high">
          <strong>
            {data.summary.too_high} of {data.summary.n}
          </strong>
          <span>Too high (hours)</span>
          <small>Hours the forecast exceeded actual generation.</small>
        </article>
        <article data-testid="summary-p90">
          <strong>{fmtMw(data.summary.p90_mw)}</strong>
          <span>90% buffer</span>
          <small>Extra cover for 9 hours in 10.</small>
        </article>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Hour (UTC)</th>
              <th>Forecast</th>
              <th>Actual</th>
              <th>Signed miss</th>
            </tr>
          </thead>
          <tbody>
            {data.hours.map((hour) => (
              <tr data-testid="hour-row" key={hour.start}>
                <th>{fmtHour(hour.start)}</th>
                <td>{fmtMw(hour.forecast_mw)}</td>
                <td>{fmtMw(hour.actual_mw)}</td>
                <td className={errorClass(hour.error_mw)}>
                  {fmtSigned(hour.error_mw)}
                  {hour.partial && <small className="partial"> partial</small>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
