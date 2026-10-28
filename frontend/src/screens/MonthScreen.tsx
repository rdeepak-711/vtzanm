import { useEffect, useState } from 'react'
import { fetchMonth, type Cutoff, type MonthResponse } from '../api'
import { fmtDate, fmtMw, fmtPct, fmtSigned } from '../format'
import { CutoffSwitch } from './CutoffSwitch'

// Reads the selected forecast cutoff from the address bar.
function readCutoff(): Cutoff {
  return new URLSearchParams(window.location.search).get('cutoff') === '09:50' ? '09:50' : '09:20'
}

// Writes the selected cutoff to the address bar.
function writeCutoff(cutoff: Cutoff) {
  window.history.pushState({}, '', `/month?cutoff=${cutoff}`)
}

// Chooses a readable tick interval for the chart axis.
function niceStep(value: number) {
  const magnitude = 10 ** Math.floor(Math.log10(Math.max(1, value)))
  const fraction = value / magnitude
  return (fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10) * magnitude
}

// Fetches the month and ignores results after the screen changes or unmounts.
function loadMonth(
  cutoff: Cutoff,
  setData: (data: MonthResponse | null) => void,
  setError: (error: string) => void,
) {
  let active = true
  setData(null)
  setError('')
  fetchMonth(cutoff)
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

// Draws hourly forecast lean bars and average miss markers.
function HourChart({ data }: { data: MonthResponse }) {
  const max = Math.max(
    1,
    ...data.by_hour_of_day.flatMap((hour) => [Math.abs(hour.bias_mw), hour.mae_mw]),
  )
  const step = niceStep(max / 4)
  const axisMax = Math.ceil(max / step) * step
  const base = 135
  const scale = 95 / axisMax
  const plotLeft = 92
  const ticks = Array.from({ length: Math.round(axisMax / step) + 1 }, (_, index) => index * step)

  return (
    <div className="chart-wrap">
      <svg
        className="month-chart"
        viewBox="0 0 780 205"
        role="img"
        aria-label="Forecast lean and average miss by hour of day"
      >
        {ticks.map((value) => {
          const y = base - value * scale
          return (
            <g key={value}>
              <line x1={plotLeft} x2="768" y1={y} y2={y} className="gridline" />
              <text x="82" y={y + 3} textAnchor="end">
                {Math.round(value).toLocaleString('en-GB')}
              </text>
            </g>
          )
        })}
        <text x="18" y="18" className="axis-title">
          MW
        </text>
        {data.by_hour_of_day.map((hour) => {
          const x = plotLeft + 7 + hour.hour * 28
          const height = Math.abs(hour.bias_mw) * scale
          return (
            <g key={hour.hour}>
              <rect
                data-testid="hod-bar"
                x={x}
                y={hour.bias_mw >= 0 ? base - height : base}
                width="14"
                height={Math.max(1, height)}
                rx="3"
                className={hour.bias_mw >= 0 ? 'bias-positive' : 'bias-negative'}
              >
                <title>
                  {String(hour.hour).padStart(2, '0')}:00 · lean {fmtSigned(hour.bias_mw)}
                </title>
              </rect>
              <circle cx={x + 7} cy={base - hour.mae_mw * scale} r="3.5" className="mae-dot">
                <title>
                  {String(hour.hour).padStart(2, '0')}:00 · average miss {fmtMw(hour.mae_mw)}
                </title>
              </circle>
              {hour.hour % 3 === 0 && (
                <text x={x + 7} y="195" textAnchor="middle">
                  {String(hour.hour).padStart(2, '0')}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

// Updates the selected cutoff and keeps the address bar in sync.
function changeCutoff(cutoff: Cutoff, setCutoff: (cutoff: Cutoff) => void) {
  setCutoff(cutoff)
  writeCutoff(cutoff)
}

// Shows month-level forecast accuracy, hourly patterns, and best and worst days.
export function MonthScreen() {
  const [cutoff, setCutoff] = useState(readCutoff)
  const [data, setData] = useState<MonthResponse | null>(null)
  const [error, setError] = useState('')

  useEffect(() => loadMonth(cutoff, setData, setError), [cutoff])

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

  const summary = data.summary
  const worst = [...data.by_day].sort((a, b) => b.mae_mw - a.mae_mw).slice(0, 3)
  const best = [...data.by_day].sort((a, b) => a.mae_mw - b.mae_mw).slice(0, 3)
  const tiles = [
    {
      id: 'tile-mae',
      title: 'Avg miss',
      value: fmtMw(summary.mae_mw),
      caption: 'Average distance between forecast and actual.',
    },
    {
      id: 'tile-bias',
      title: 'Lean',
      value: fmtSigned(summary.bias_mw),
      caption: '+ means the forecast was higher than what arrived.',
    },
    {
      id: 'tile-too-high',
      title: 'Too high (hours)',
      value: `${summary.too_high} of ${summary.n} (${fmtPct(summary.share_too_high)})`,
      caption: 'Hours the forecast exceeded actual generation.',
    },
    {
      id: 'tile-p90',
      title: '90% buffer',
      value: fmtMw(summary.p90_mw),
      caption: 'Extra cover for 9 hours in 10.',
    },
  ]

  return (
    <section className="content">
      <div className="screen-heading">
        <div>
          <p className="eyebrow">MONTHLY REVIEW</p>
          <h1>January 2026</h1>
        </div>
        <CutoffSwitch cutoff={cutoff} onChange={(value) => changeCutoff(value, setCutoff)} />
      </div>
      <div className="summary-grid month-tiles">
        {tiles.map((tile) => (
          <article data-testid={tile.id} key={tile.id}>
            <strong>{tile.value}</strong>
            <span>{tile.title}</span>
            <small>{tile.caption}</small>
          </article>
        ))}
      </div>
      <p className="off-count">
        Off by 1,000 MW or more in{' '}
        <strong>
          {data.hours_off_by_1000} of {summary.n} hours
        </strong>
      </p>
      <div className="panel">
        <HourChart data={data} />
        <div className="legend">
          <span>
            <i className="key bias-key" />
            Lean
          </span>
          <span>
            <i className="key mae-key" />
            Average miss
          </span>
        </div>
      </div>
      <h2>Worst and best days</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Day</th>
              <th>Avg miss</th>
              <th>Lean</th>
              <th>Too high</th>
            </tr>
          </thead>
          <tbody>
            {[...worst, ...best].map((day, index) => (
              <tr data-testid="day-row" key={`${index}-${day.date}`}>
                <th>
                  <a href={`/?date=${day.date}&cutoff=${cutoff}`}>{fmtDate(day.date)}</a>
                </th>
                <td>{fmtMw(day.mae_mw)}</td>
                <td className={day.bias_mw > 0 ? 'positive' : day.bias_mw < 0 ? 'negative' : ''}>
                  {fmtSigned(day.bias_mw)}
                </td>
                <td>
                  {day.too_high} of {day.n}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <aside className="reading-note">
        <h2>How to read this</h2>
        <p>
          Error is forecast − actual. The lean is correctable by shifting the forecast. The buffer
          covered 9 hours in 10 in January, one winter month only.
        </p>
      </aside>
    </section>
  )
}
