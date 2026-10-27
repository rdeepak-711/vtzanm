# Spec — Day-ahead wind forecast app (Gridbricks / REint challenge)

## Goal

A web app for a UK energy supplier's day-ahead buying team. For any delivery day in January 2026 it shows the wind forecast the team actually had at the moment the auction closed (Screen 1), and it measures how wrong those forecasts were over the month, in numbers a buyer can act on (Screen 2).

Out of scope: a "how much to buy" figure (no demand data, D9), solar or any dataset beyond Elexon FUELHH and WINDFOR, live Elexon calls at page load (D6), user accounts, a map, forecast-run comparison tools, anything after 1 Feb 2026. The curtailment explanation (D10) is said in the video, not built.

Every rule below comes from `docs/decisions.md` (D1–D11). Read that file before building; the D-numbers in this spec point at it.

Test command: `python3 -m pytest tests -q -p no:cacheprovider && npm --prefix frontend test -- --run`

Setup command: `python3 -m pip install -r requirements.txt && npm --prefix frontend install --no-audit --no-fund`

Preview command: `npm --prefix frontend run build && python3 -m uvicorn windapp.main:app --app-dir backend --host 0.0.0.0 --port $PORT`

Preview pages: `/, /month, /?date=2026-01-15, /?date=2026-01-28&cutoff=09:50`

## The data (already in the repo)

- `data/windfor_2026-01.json`: raw WINDFOR rows from the Elexon stream endpoint, a JSON list. Each row: `dataset`, `publishTime` (ISO, UTC, "Z"), `startTime`, `generation` (MW, integer). 17,885 rows; publish times from 2026-01-01T02:30Z to 2026-01-31T11:30Z; 8 runs a day at 02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30, 22:30 UTC; each run has 73 hourly rows from 21:00 the day before the run to 21:00 two days after.
- `data/fuelhh_2026-01.json`: raw FUELHH rows, fuelType WIND only, a JSON list. Each row: `dataset`, `publishTime`, `startTime`, `settlementDate`, `settlementPeriod`, `fuelType`, `generation` (MW, average over 30 min). 1,488 rows = 48 a day from 2026-01-02T00:00Z to 2026-02-01T23:30Z.
- These two files are the only data the app reads. They are fixtures for the tests and the source for the deployed app. `scripts/refresh_data.py` re-downloads them (step 2) but never runs in tests.
- January 2026 UK time is UTC, so every time in this app is UTC and no conversion is done. Timestamps are parsed as timezone-aware UTC `datetime`s and never compared with naive ones.

## Domain rules (what the code must do)

1. **Delivery days (D1):** 2026-01-02 to 2026-02-01 inclusive, 31 days, 744 hours. A request for any other date is rejected with HTTP 400 and a message that says the allowed range.
2. **Cutoff (D2):** `"09:20"` (default) or `"09:50"`. The decision time for delivery day D is D-1 at the cutoff, UTC. Any other cutoff string is rejected with HTTP 400.
3. **Pick rule (D3):** for each delivery hour H of day D, consider WINDFOR rows with `startTime == H`, ignore rows where `startTime < publishTime` (stale copies of past hours), keep rows with `publishTime <= decision_time`, and use the one with the latest `publishTime`. Record that `publishTime` as the run used and `lead_hours = (H − publishTime)` in hours, as a float with one decimal. If no row qualifies, the hour is `forecast_mw: null` and excluded from the error numbers; this never happens in the January data but the code must not crash on it.
4. **Actual (D4):** actual MW for hour H = mean of the FUELHH `generation` values whose `startTime` is H:00 and H:30. If only one exists, use it and set `partial: true`. If neither exists, `actual_mw: null` and the hour is excluded from the error numbers. January has 0 partial hours.
5. **Error (D5):** `error_mw = forecast_mw − actual_mw`. Positive means the forecast was too high (the buyer ends up short).
6. **Summary numbers (D5)** over a list of errors e₁…eₙ (n ≥ 1):
   - `n`: count.
   - `mae_mw`: mean of |eᵢ|.
   - `bias_mw`: mean of eᵢ.
   - `too_high`: count of eᵢ > 0. `share_too_high`: too_high / n as a float, not rounded (the UI formats it as a percentage).
   - `p90_mw`: sort the errors ascending and take the value at 1-based rank ⌈0.9·n⌉ (nearest-rank method, no interpolation). For n = 744 this is rank 670; for n = 24 it is rank 22.
   - `max_error_mw`: the largest eᵢ. `min_error_mw`: the smallest eᵢ (most negative, or the smallest positive if none is negative).
   - All MW values are floats rounded to 1 decimal.
   - An empty list gives a summary with `n: 0` and every other field `null`.
7. **Month view (D5, D8):** over all 744 hours for one cutoff: the summary, the summary per hour of day (24 entries, `hour` 0–23, n = 31 each), the summary per delivery day (31 entries, with `date`), and `hours_off_by_1000`: count of |eᵢ| ≥ 1000.

## Expected numbers (acceptance values, computed 27 Oct 2026 from the data files above; tolerance ±1 MW unless stated)

Cutoff 09:20:
- Every hour's run used is D-1 at 07:30 (so for 2026-01-15 it is `2026-01-14T07:30:00Z`); lead hours run from 16.5 (hour 00) to 39.5 (hour 23).
- Month: n 744, mae 2038.9, bias 1747.9, too_high 632, p90 4098.5, max 6870.0, min −3550.0, hours_off_by_1000 552, 0 partial hours.
- Hour of day 0: n 31, mae 2027.8, bias 1952.7, too_high 29. Hour of day 12: mae 1929.3, bias 1387.7, too_high 24.
- 15 Jan: n 24, mae 1041.8, bias 1041.8, too_high 24, p90 1633.5, max 1812.5, min 242.0. Hour 00: forecast 15834, actual 14456.5, error 1377.5. Hour 01: forecast 15478, actual 14358.0, error 1120.0. Hour 12: forecast 11049, actual 9790.5, error 1258.5.
- Worst days by mae: 28 Jan (5374.8), 12 Jan (4868.2), 11 Jan (4801.6). Best: 19 Jan (736.1).

Cutoff 09:50:
- Every hour's run used is D-1 at 09:30.
- Month: n 744, mae 2013.0, bias 1729.9, too_high 627, p90 4145.5, max 6833.0, min −4128.0.

## Architecture

```
gridbricks-challenge/
├── spec/site.md                 this file
├── docs/decisions.md            D1–D11 (exists); flow.md and mental-model.md are written by Claude at review time
├── data/                        the two JSON fixtures (exist)
├── scripts/refresh_data.py      re-downloads the two files from Elexon (step 2)
├── backend/windapp/             Python package, pure logic + FastAPI
│   ├── __init__.py
│   ├── load.py                  read the JSON files into typed rows
│   ├── pick.py                  the pick rule (D3)
│   ├── actuals.py               hourly actuals (D4)
│   ├── metrics.py               errors + summaries (D5)
│   ├── service.py               day_view / month_view, cached in-process
│   └── main.py                  FastAPI app, 3 endpoints, serves frontend/dist when it exists
├── api/index.py                 Vercel entry: puts backend/ on sys.path and exposes `app`
├── frontend/                    Vite + React + TypeScript
│   └── src/ main.tsx, App.tsx, api.ts, format.ts, screens/DayScreen.tsx, screens/MonthScreen.tsx, __tests__/
├── tests/                       pytest acceptance tests (exist, failing)
├── requirements.txt, pytest.ini, vercel.json, docker-compose.yml, Dockerfile, .dockerignore, .gitignore, README.md
```

Execution path: a browser request hits the React app (static files from `frontend/dist`); the app calls `GET /api/day` or `GET /api/month`; FastAPI (`main.py`) validates the query, calls `service.py`, which on first use loads both JSON files via `load.py`, runs `pick.py` + `actuals.py` + `metrics.py`, caches the result per (date, cutoff) and per cutoff, and returns JSON. Locally everything runs in one uvicorn process (Docker or the preview command). On Vercel the static files come from the CDN and `/api/*` runs as a Python serverless function via `api/index.py`; Docker is not what runs on Vercel (D7) and the README says so.

### Python modules and exports (the tests import exactly these names)

`windapp.load`
- `ForecastRow(publish_time: datetime, start_time: datetime, generation_mw: int)` (frozen dataclass)
- `ActualRow(start_time: datetime, generation_mw: int)` (frozen dataclass)
- `load_windfor(path: Path) -> list[ForecastRow]`, `load_fuelhh(path: Path) -> list[ActualRow]`. Both parse "Z" as UTC. `load_fuelhh` keeps only rows whose `fuelType == "WIND"`.
- `DATA_DIR: Path` (the repo's `data/` folder, resolved relative to this file), `WINDFOR_PATH`, `FUELHH_PATH`.

`windapp.pick`
- `CUTOFFS = {"09:20": time(9, 20), "09:50": time(9, 50)}`
- `decision_time(delivery_day: date, cutoff: str) -> datetime` (UTC, D-1 at the cutoff; raises `ValueError` for an unknown cutoff)
- `PickedHour(start_time: datetime, forecast_mw: int | None, run_published: datetime | None, lead_hours: float | None)` (frozen dataclass)
- `pick_day(rows: list[ForecastRow], delivery_day: date, cutoff: str) -> list[PickedHour]` returns exactly 24 entries in hour order.

`windapp.actuals`
- `HourActual(start_time: datetime, actual_mw: float | None, partial: bool)` (frozen dataclass)
- `hourly_actuals(rows: list[ActualRow]) -> dict[datetime, HourActual]` keyed by the hour's start time (minute 0).

`windapp.metrics`
- `Summary` (frozen dataclass with the fields in rule 6: `n`, `mae_mw`, `bias_mw`, `too_high`, `share_too_high`, `p90_mw`, `max_error_mw`, `min_error_mw`)
- `summarise(errors: list[float]) -> Summary`
- `p90(errors: list[float]) -> float` (nearest rank, rule 6)

`windapp.service`
- `DELIVERY_FROM = date(2026, 1, 2)`, `DELIVERY_TO = date(2026, 2, 1)`
- `day_view(delivery_day: date, cutoff: str = "09:20") -> dict` (the `/api/day` body; raises `ValueError` for an out-of-range day or bad cutoff)
- `month_view(cutoff: str = "09:20") -> dict` (the `/api/month` body)

`windapp.main`
- `app` (FastAPI). Endpoints below. After the API routes, if `frontend/dist` exists it is mounted at `/` with `StaticFiles(html=True)` so `/` and `/month` both return `index.html` (the React app does client-side routing with the pathname; no router library is needed).

`scripts/refresh_data.py`
- `elexon_urls(publish_from: datetime, publish_to: datetime, settlement_from: date, settlement_to: date) -> tuple[str, str]` returns (WINDFOR url, FUELHH url): `https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream?publishDateTimeFrom=...&publishDateTimeTo=...` and `https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream?settlementDateFrom=...&settlementDateTo=...&fuelType=WIND`, times formatted `YYYY-MM-DDTHH:MMZ`.
- `main()` downloads with the standard library only (`urllib`), for publish 2026-01-01T00:00Z → 2026-02-01T00:00Z and settlement 2026-01-02 → 2026-02-01, and writes the two files with `json.dump(..., indent=0)`. Tests import `elexon_urls` only; they never call `main()`.

### API

`GET /api/health` → 200 `{"status": "ok", "delivery_days": {"from": "2026-01-02", "to": "2026-02-01"}, "cutoffs": ["09:20", "09:50"]}`

`GET /api/day?date=YYYY-MM-DD&cutoff=09:20` (`cutoff` optional, default 09:20) → 200:
```json
{
  "date": "2026-01-15",
  "cutoff": "09:20",
  "decision_time": "2026-01-14T09:20:00Z",
  "runs_used": ["2026-01-14T07:30:00Z"],
  "hours": [
    {"start": "2026-01-15T00:00:00Z", "forecast_mw": 15834, "actual_mw": 14456.5, "error_mw": 1377.5,
     "run_published": "2026-01-14T07:30:00Z", "lead_hours": 16.5, "partial": false}
  ],
  "summary": {"n": 24, "mae_mw": 1041.8, "bias_mw": 1041.8, "too_high": 24, "share_too_high": 1.0,
              "p90_mw": 1633.5, "max_error_mw": 1812.5, "min_error_mw": 242.0}
}
```
`hours` always has 24 entries. `runs_used` is the sorted distinct list of `run_published` values. Times are ISO 8601 with a trailing `Z`. Missing `date`, a date outside the range, an unparseable date, or an unknown cutoff → 400 with `{"detail": "..."}` that names the allowed range or the allowed cutoffs.

`GET /api/month?cutoff=09:20` → 200:
```json
{
  "cutoff": "09:20",
  "from": "2026-01-02", "to": "2026-02-01",
  "summary": {"n": 744, "...": "same fields as above"},
  "hours_off_by_1000": 552,
  "partial_hours": 0,
  "by_hour_of_day": [{"hour": 0, "n": 31, "mae_mw": 2027.8, "bias_mw": 1952.7, "too_high": 29, "share_too_high": 0.9354838709677419, "p90_mw": 3937.0, "max_error_mw": 6758.0, "min_error_mw": -605.5}],
  "by_day": [{"date": "2026-01-02", "n": 24, "mae_mw": 0.0, "bias_mw": 0.0, "too_high": 0, "share_too_high": 0.0, "p90_mw": 0.0, "max_error_mw": 0.0, "min_error_mw": 0.0, "runs_used": ["..."]}]
}
```
`by_hour_of_day` has 24 entries in hour order; `by_day` has 31 entries in date order (values above are placeholders for shape only, except hour 0 which is real).

### Frontend (D8: two screens, nothing else)

Vite + React 19 + TypeScript (as shipped by the Vite template), no router library, no chart library, no CSS framework: plain CSS in `src/styles.css`, and SVG drawn by hand for the two charts. Light theme, readable on a phone at 390 px wide. `src/api.ts` exports `fetchDay(date, cutoff)` and `fetchMonth(cutoff)` calling the endpoints above with `fetch`, relative URLs (`/api/...`), and throwing an `Error` with the server's `detail` on a non-200. `src/format.ts` exports `fmtMw(n: number | null): string` ("15,834 MW" / "—"), `fmtSigned(n)` ("+1,377.5 MW" / "−605.5 MW"), and `fmtRun(iso)` ("14 Jan 07:30").

Routing: `App.tsx` reads `window.location.pathname`; `/month` renders `MonthScreen`, anything else renders `DayScreen`. Both screens read `cutoff` from the query string (default 09:20) and `DayScreen` reads `date` (default 2026-01-15). Changing the date or the cutoff updates the URL with `history.pushState` and refetches. A top bar has two links, "Day" (`/`) and "Month" (`/month`), both keeping the current `cutoff`, and the cutoff switch: two buttons, 09:20 (EPEX) and 09:50 (N2EX), the active one marked with `aria-pressed="true"`.

`DayScreen` (`/`): a date input limited to 2026-01-02 … 2026-02-01 with previous/next buttons; a line "Decision time: 14 Jan 2026 09:20 · Forecast run used: 14 Jan 07:30 (16.5–39.5 h ahead)" (if more than one run was used, list them); an SVG line chart of forecast vs actual over the 24 hours with a legend; a table with one row per hour: hour, forecast, actual, error (signed, red when positive, blue when negative), and "partial" shown when the flag is true; a summary strip with "Avg miss", "Lean", "Too high (hours)", "90% buffer", each with a one-line plain-words caption (e.g. Lean: "+ means the forecast was higher than what arrived"). The 24 hourly rows and the summary strip use `data-testid="hour-row"` and `data-testid="summary-<field>"` (`mae`, `bias`, `too_high`, `p90`).

`MonthScreen` (`/month`): four tiles (`data-testid="tile-mae"`, `tile-bias`, `tile-too-high`, `tile-p90`) with the month numbers and captions, plus a line "Off by 1,000 MW or more in 552 of 744 hours"; an SVG bar chart of `bias_mw` by hour of day (24 bars, `data-testid="hod-bar"`) with `mae_mw` shown as a dot or thin bar per hour and a legend; a "Worst and best days" table: the 3 highest-mae days and the 3 lowest (`data-testid="day-row"`), each with date, avg miss, lean, hours too high, and a link to that day on the Day screen; and a short "How to read this" note, 3 sentences max, saying: error = forecast − actual; the lean is correctable by shifting the forecast; the buffer is the extra cover that would have covered 9 hours in 10 in January, which is one winter month only.

Loading and error states: while fetching show "Loading…"; on an error show the message in a `role="alert"` element. No other states.

Vitest + React Testing Library + jsdom, tests in `frontend/src/__tests__/` (exist, failing). `fetch` is mocked per test with fixture objects shaped like the API; no network. `package.json` must have `"test": "vitest"` and `"build": "tsc -b && vite build"` (or `vite build` alone if tsc is too slow; type errors must still be zero).

### Packaging and deploy

- `requirements.txt`: `fastapi`, `uvicorn`, `httpx` (for FastAPI's TestClient), `pytest`. Pin exact versions.
- `pytest.ini`: `[pytest]` with `pythonpath = backend scripts` and `testpaths = tests`.
- `api/index.py`: inserts `<repo>/backend` into `sys.path`, then `from windapp.main import app`.
- `vercel.json`: `buildCommand` = `npm --prefix frontend install --no-audit --no-fund && npm --prefix frontend run build`, `outputDirectory` = `frontend/dist`, `rewrites`: `/api/(.*)` → `/api/index`, and a fallback rewrite of `/((?!api/).*)` → `/index.html` so `/month` loads the app. The Python runtime version is left to Vercel's default (3.12) unless the deploy fails on it.
- `Dockerfile` (one image): node stage builds `frontend/dist`; python stage installs `requirements.txt`, copies `backend/`, `data/`, and the built `dist` into `frontend/dist`, runs `uvicorn windapp.main:app --app-dir backend --host 0.0.0.0 --port 8000`. `docker-compose.yml`: one service `app`, port 8000:8000. `.dockerignore` excludes `node_modules`, `.git`, `docs/learn`, `tests`.
- `.gitignore` (exists, D11): `docs/learn/`, `docs/*.pdf`, `node_modules/`, `frontend/dist/`, `__pycache__/`, `.venv/`, `.vercel/`, `.env*`.
- `README.md` (step 7): what the app does in 3 lines; a tree of files and directories with one line each; how to start (Docker: `docker compose up` then http://localhost:8000; without Docker: the setup command, `npm --prefix frontend run build`, then the uvicorn command); the deployed Vercel link; how to re-download the data; the decisions summary with a link to `docs/decisions.md`; a paragraph "AI tools used" stating that Claude Code (Anthropic) was used for research, planning, the spec and tests, and reviews, Codex (OpenAI) wrote the implementation, and Gemini (Google) orchestrated, with the author steering and reviewing every step; a "Not what Vercel runs" note about Docker; time spent.

## Files the builder may create or change

Create or change: `backend/windapp/**`, `scripts/refresh_data.py`, `api/index.py`, `frontend/**` except `frontend/src/__tests__/**`, `requirements.txt`, `pytest.ini`, `vercel.json`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `README.md`.

Do not change: `spec/**`, `tests/**`, `frontend/src/__tests__/**`, `data/**`, `docs/**`, `.gitignore`. If a test looks wrong, say so in the step report and stop; do not edit it.

## Build order (bottom up; a step is not started until the previous one's tests pass)

1. **Load + pick + actuals + metrics (pure logic).** Files: `backend/windapp/{__init__,load,pick,actuals,metrics}.py`, `requirements.txt`, `pytest.ini`. Behaviour: rules 1–6. Edge cases: stale rows (startTime < publishTime) ignored; rows published after the cutoff ignored even when newer; a later run that is missing falls back to an earlier run with a longer lead; a missing half-hour gives `partial: true`; an hour with no forecast or no actual gives `None`; `summarise([])` gives n 0 and nulls; `p90` on 24 values takes rank 22; "Z" parsed as UTC. Tests: `tests/test_load.py`, `tests/test_pick.py`, `tests/test_actuals.py`, `tests/test_metrics.py`.
2. **Refresh script.** File: `scripts/refresh_data.py`. Behaviour: the URLs in the module list above; `main()` guarded by `if __name__ == "__main__":`. Tests: `tests/test_refresh.py` (URL builder only).
3. **Service layer.** File: `backend/windapp/service.py`. Behaviour: `day_view` and `month_view` build the API bodies from steps 1's functions, cached with `functools.lru_cache`; out-of-range day or bad cutoff raises `ValueError`. Tests: `tests/test_service.py` (the acceptance values above, both cutoffs, the 15 Jan hours, 24 and 31 entry counts, `runs_used`).
4. **FastAPI.** Files: `backend/windapp/main.py`, `api/index.py`. Behaviour: the three endpoints, 400s with a helpful `detail`, JSON shapes exactly as above, static mount only if `frontend/dist` exists. Tests: `tests/test_api.py` (FastAPI `TestClient`).
5. **Frontend.** Files: `frontend/**` (package.json, vite config, tsconfig, index.html, src). Behaviour: the two screens as specified; `api.ts` and `format.ts`. Tests: `frontend/src/__tests__/{format,api,DayScreen,MonthScreen}.test.tsx`. Then `npm --prefix frontend run build` must succeed and the preview pages must render.
6. **Packaging.** Files: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `vercel.json`. Behaviour: `docker compose up` serves the app on 8000 with `/api/health` and `/` both working; `vercel.json` as above. Tests: none automated; the step report must include the output of `curl localhost:8000/api/health` from the running container.
7. **README.** File: `README.md` as specified. Tests: `tests/test_readme.py` (required headings and phrases present).

End-to-end check after step 7: run the Test command; run the preview command and open the four preview pages on a phone width and a desktop; `docker compose up` and hit `/api/day?date=2026-01-15`. Deploying to Vercel and the video are done by Deepak with Claude, outside the build.

## Done means

- The Test command exits 0 with every test passing, none skipped.
- `/api/month` returns the acceptance values for both cutoffs; `/api/day?date=2026-01-15` returns the 15 Jan values.
- Both screens render the real data on a phone and a desktop with no console errors; the cutoff switch and the date controls change the URL and the numbers.
- `docker compose up` works from a clean clone.
- README matches the repo as built.
- Not part of "done" for the builder, but part of the submission: deployed on Vercel at a public URL that works in incognito; public GitHub repo with a random name; the unlisted video; the form.
