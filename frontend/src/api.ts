export type Cutoff = '09:20' | '09:50'
export interface Summary { n: number; mae_mw: number; bias_mw: number; too_high: number; share_too_high: number; p90_mw: number; max_error_mw: number; min_error_mw: number }
export interface DayHour { start: string; forecast_mw: number | null; actual_mw: number | null; error_mw: number | null; run_published: string; lead_hours: number; partial: boolean }
export interface DayResponse { date: string; cutoff: Cutoff; decision_time: string; runs_used: string[]; hours: DayHour[]; summary: Summary }
export interface HourSummary extends Summary { hour: number }
export interface MonthDay extends Summary { date: string; runs_used: string[] }
export interface MonthResponse { cutoff: Cutoff; from: string; to: string; summary: Summary; hours_off_by_1000: number; partial_hours: number; by_hour_of_day: HourSummary[]; by_day: MonthDay[] }

async function bodyOrError<T>(url: string): Promise<T> {
  const res = await fetch(url)
  const body = await res.json()
  if (!res.ok) throw new Error(body.detail)
  return body as T
}

export function fetchDay(date: string, cutoff: string): Promise<DayResponse> {
  return bodyOrError<DayResponse>(`/api/day?date=${date}&cutoff=${cutoff}`)
}

export function fetchMonth(cutoff: string): Promise<MonthResponse> {
  return bodyOrError<MonthResponse>(`/api/month?cutoff=${cutoff}`)
}
