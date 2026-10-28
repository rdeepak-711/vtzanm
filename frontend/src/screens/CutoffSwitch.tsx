import type { Cutoff } from '../api'

export function CutoffSwitch({ cutoff, onChange }: { cutoff: Cutoff; onChange: (value: Cutoff) => void }) {
  return <div className="cutoff-switch" aria-label="Decision cutoff">
    <button type="button" aria-pressed={cutoff === '09:20'} onClick={() => onChange('09:20')}>09:20 EPEX</button>
    <button type="button" aria-pressed={cutoff === '09:50'} onClick={() => onChange('09:50')}>09:50 N2EX</button>
  </div>
}
