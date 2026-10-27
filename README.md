# Day-ahead wind forecast

A web app for a UK electricity supplier's day-ahead buying team. The team buys power a day before it is delivered, so it has to plan around a wind forecast. For every delivery day in January 2026, the app shows the wind forecast the team actually had when the auction closed, and measures how wrong those forecasts turned out to be, in numbers a buyer can act on.

Data: Elexon [FUELHH](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) (actual national wind generation, fuelType WIND) and [WINDFOR](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) (national wind forecasts). No other data.

## Status

Work in progress. The spec, the decisions and the January data are in the repo; the build follows the spec bottom up (logic, then API, then UI), with tests written before the code.

## How it works

1. **Decision time.** A day-ahead buyer decides on the morning before delivery. The default cutoff is 09:20 UK time (EPEX GB day-ahead auction close), with 09:50 (Nord Pool N2EX) as an option. January UK time equals UTC.
2. **The forecast they had.** For each delivery hour, the app takes the newest WINDFOR forecast published at or before the cutoff. Anything published later is hindsight and is ignored. In January 2026 this is the 07:30 UTC run of the day before.
3. **What actually came.** The actual for each hour is the average of its two half-hour FUELHH readings.
4. **How wrong it was.** Error = forecast − actual, so a positive error means the forecast was too high and the buyer ended up short. The app reports the average miss, the lean (average signed error), and a 90% buffer (the extra cover that would have been enough in 9 hours out of 10), for the month, by hour of day and by day.

Every rule, with the alternatives considered and what it costs, is in [docs/decisions.md](docs/decisions.md).

## Files and directories

```text
.
├── spec/site.md        the build spec: rules, expected numbers, architecture, build order
├── docs/decisions.md   decisions log (what was decided, alternatives, why, cost)
├── findings.md         research notes: Elexon definitions, data checks, open questions
├── data/
│   ├── windfor_2026-01.json   WINDFOR rows published 1–31 Jan 2026
│   └── fuelhh_2026-01.json    FUELHH wind rows for 2 Jan – 1 Feb 2026
└── frontend/           Vite + React + TypeScript app (base template for now)
```

`backend/` (Python, FastAPI), `api/` (Vercel entry), `scripts/` (data download), `tests/` and the Docker files are added during the build.

## How to start

For now only the frontend shell runs:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Full instructions (Docker, and the Python API without Docker) come with the build.

## Live app

Link added after deployment to Vercel.

## AI tools used

Claude Code (Anthropic) for domain research, planning, the spec, tests and code review; Codex (OpenAI) for writing code. The author steers and reviews every step.
