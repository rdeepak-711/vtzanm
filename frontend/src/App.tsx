import { DayScreen } from './screens/DayScreen'
import { MonthScreen } from './screens/MonthScreen'

export default function App() {
  const cutoff = new URLSearchParams(window.location.search).get('cutoff') === '09:50' ? '09:50' : '09:20'
  return <>
    <header className="topbar"><a className="brand" href={`/?cutoff=${cutoff}`}>Wind / forecast review</a><nav aria-label="Main navigation"><a href={`/?cutoff=${cutoff}`}>Day</a><a href={`/month?cutoff=${cutoff}`}>Month</a></nav></header>
    <main>{window.location.pathname === '/month' ? <MonthScreen /> : <DayScreen />}</main>
    <footer>Wind forecast review <span>· UTC throughout</span></footer>
  </>
}
