import { useEffect, useState } from 'react'
import { fetchDay, type Cutoff, type DayResponse } from '../api'
import { fmtDate, fmtHour, fmtMw, fmtRun, fmtSigned } from '../format'
import { CutoffSwitch } from './CutoffSwitch'

const firstDay = '2026-01-02'
const lastDay = '2026-02-01'
function query() { const q = new URLSearchParams(window.location.search); return { date: q.get('date') || '2026-01-15', cutoff: (q.get('cutoff') === '09:50' ? '09:50' : '09:20') as Cutoff } }
function setQuery(date: string, cutoff: Cutoff) { window.history.pushState({}, '', `/?date=${date}&cutoff=${cutoff}`) }

function Lines({ data }: { data: DayResponse }) {
  const vals = data.hours.flatMap(h => [h.forecast_mw ?? 0, h.actual_mw ?? 0])
  const min = Math.min(...vals), max = Math.max(...vals), span = max - min || 1
  const y = (v: number | null) => 170 - (((v ?? min) - min) / span) * 145
  const points = (key: 'forecast_mw' | 'actual_mw') => data.hours.map((h, i) => `${24 + i * 24},${y(h[key])}`).join(' ')
  return <div className="chart-wrap"><svg className="day-chart" viewBox="0 0 600 205" role="img" aria-label="Forecast and actual wind by hour in UTC">
    {[0, 1, 2, 3].map(i => <line key={i} x1="24" x2="576" y1={25 + i * 48} y2={25 + i * 48} className="gridline" />)}
    <polyline points={points('forecast_mw')} className="line-forecast" /> <polyline points={points('actual_mw')} className="line-actual" />
    {[0, 6, 12, 18, 23].map(h => <text key={h} x={24 + h * 24} y="198" textAnchor="middle">{String(h).padStart(2, '0')}</text>)}
  </svg></div>
}

export function DayScreen() {
  const initial = query()
  const [date, setDate] = useState(initial.date)
  const [cutoff, setCutoff] = useState(initial.cutoff)
  const [data, setData] = useState<DayResponse | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { let active = true; setData(null); setError(''); fetchDay(date, cutoff).then(v => { if (active) setData(v) }).catch(e => { if (active) setError(e.message) }); return () => { active = false } }, [date, cutoff])
  function changeDate(value: string) { if (!value) return; setDate(value); setQuery(value, cutoff) }
  function changeCutoff(value: Cutoff) { setCutoff(value); setQuery(date, value) }
  function shift(days: number) { const d = new Date(`${date}T00:00:00Z`); d.setUTCDate(d.getUTCDate() + days); changeDate(d.toISOString().slice(0, 10)) }
  if (error) return <section className="content"><p role="alert">{error}</p></section>
  if (!data) return <section className="content"><p>Loading…</p></section>
  const runs = [...new Set(data.runs_used)]
  const lead = data.hours.length ? `${Math.min(...data.hours.map(h => h.lead_hours))}–${Math.max(...data.hours.map(h => h.lead_hours))} h ahead` : ''
  return <section className="content">
    <div className="screen-heading"><div><p className="eyebrow">DAILY REVIEW</p><h1>{fmtDate(date, true)}</h1></div><CutoffSwitch cutoff={cutoff} onChange={changeCutoff} /></div>
    <div className="date-controls"><button aria-label="Previous day" disabled={date <= firstDay} onClick={() => shift(-1)}>←</button><input aria-label="Delivery date" type="date" min={firstDay} max={lastDay} value={date} onChange={e => changeDate(e.target.value)} /><button aria-label="Next day" disabled={date >= lastDay} onClick={() => shift(1)}>→</button></div>
    <p className="decision">Decision time: {fmtDate(data.decision_time.slice(0, 10), true)} {fmtHour(data.decision_time)} · Forecast run used: {runs.map(fmtRun).join(', ')}{lead ? ` (${lead})` : ''}</p>
    <div className="panel"><Lines data={data} /><div className="legend"><span><i className="key forecast" />Forecast</span><span><i className="key actual" />Actual</span></div></div>
    <div className="summary-grid">
      <article data-testid="summary-mae"><strong>{fmtMw(data.summary.mae_mw)}</strong><span>Avg miss</span><small>Average distance between forecast and actual.</small></article>
      <article data-testid="summary-bias"><strong>{fmtSigned(data.summary.bias_mw)}</strong><span>Lean</span><small>+ means the forecast was higher than what arrived.</small></article>
      <article data-testid="summary-too_high"><strong>{data.summary.too_high} of {data.summary.n}</strong><span>Too high (hours)</span><small>Hours the forecast exceeded actual generation.</small></article>
      <article data-testid="summary-p90"><strong>{fmtMw(data.summary.p90_mw)}</strong><span>90% buffer</span><small>Extra cover for 9 hours in 10.</small></article>
    </div>
    <div className="table-wrap"><table><thead><tr><th>Hour (UTC)</th><th>Forecast</th><th>Actual</th><th>Signed miss</th></tr></thead><tbody>{data.hours.map(h => <tr data-testid="hour-row" key={h.start}><th>{fmtHour(h.start)}</th><td>{fmtMw(h.forecast_mw)}</td><td>{fmtMw(h.actual_mw)}</td><td className={h.error_mw === null ? '' : h.error_mw > 0 ? 'positive' : h.error_mw < 0 ? 'negative' : ''}>{fmtSigned(h.error_mw)}{h.partial && <small className="partial"> partial</small>}</td></tr>)}</tbody></table></div>
  </section>
}
