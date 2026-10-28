# Day-ahead wind forecast

A web app for a UK electricity supplier's day-ahead buying team. The team buys power a day before it is delivered, so it has to plan around a wind forecast. For every delivery day in January 2026, the app shows the wind forecast the team actually had when the auction closed, and measures how wrong those forecasts turned out to be, in numbers a buyer can act on.

Data: Elexon [FUELHH](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) (actual national wind generation, fuelType WIND) and [WINDFOR](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) (national wind forecasts). No other data.

## How it works

1. **Decision time.** A day-ahead buyer decides on the morning before delivery. The default cutoff is 09:20 UK time (EPEX GB day-ahead auction close), with 09:50 (Nord Pool N2EX) as an option. January UK time equals UTC.
2. **The forecast they had.** For each delivery hour, the app takes the newest WINDFOR forecast published at or before the cutoff. Anything published later is hindsight and is ignored. In January 2026 this is the 07:30 UTC run of the day before.
3. **What actually came.** The actual for each hour is the average of its two half-hour FUELHH readings.
4. **How wrong it was.** Error = forecast − actual, so a positive error means the forecast was too high and the buyer ended up short. The app reports the average miss, the lean (average signed error), and a 90% buffer (the extra cover that would have been enough in 9 hours out of 10), for the month, by hour of day and by day.

Every rule, with the alternatives considered and what it costs, is in [docs/decisions.md](docs/decisions.md).

## Live app

https://vtzanm.vercel.app

Day screen: choose a delivery date and forecast cutoff to review the forecast, actual generation, and hourly miss.

/month: review monthly performance by day and by hour of day.

## Files and directories

```text
.
├── backend/windapp/       Python app (FastAPI)
│   ├── load.py            reads the saved Elexon JSON, rejects times without a zone
│   ├── pick.py            per hour: newest forecast published at or before the cutoff
│   ├── actuals.py         per hour: average of the two half-hour FUELHH readings
│   ├── metrics.py         report card: average miss, lean, too-high share, 90% buffer
│   ├── service.py         joins the above into day and month views (cached)
│   └── main.py            HTTP routes /api/health, /api/day, /api/month + serves the built frontend
├── frontend/              Vite + React + TypeScript: Day screen and Month screen
├── api/index.py           Vercel entry point, imports the FastAPI app
├── scripts/refresh_data.py  downloads January 2026 from Elexon into data/
├── data/                  the saved WINDFOR and FUELHH responses, unchanged
├── tests/                 pytest suite (frontend tests live in frontend/src/__tests__)
├── spec/site.md           build spec: rules, expected numbers, architecture
├── docs/decisions.md      decisions log: what was decided, alternatives, why, cost
├── findings.md            research notes on the Elexon data
├── Dockerfile             builds the frontend, then runs the app on port 8000
├── docker-compose.yml     one service, port 8000
└── vercel.json            Vercel build command, SPA rewrite, files bundled with the function
```

## How to start

With Docker:

```bash
docker compose up --build
```

Open http://localhost:8000.

Without Docker, install the Python dependencies from the root requirements file and build the frontend:

```bash
pip install -r requirements.txt
npm --prefix frontend install
npm --prefix frontend run build
```

Then from `backend/`, start the API:

```bash
uvicorn windapp.main:app --port 8000
```

For development, run the API from `backend/` and run Vite in a second terminal; the Vite proxy forwards `/api` requests to `http://localhost:8000`:

```bash
uvicorn windapp.main:app --port 8000
npm --prefix frontend run dev
```

Run the tests with:

```bash
python3 -m pytest tests -q -p no:cacheprovider
npm --prefix frontend test -- --run
```

## Data

Data is downloaded once from Elexon by `python3 scripts/refresh_data.py` and saved as JSON in `data/`; restart the app after a refresh because results are cached.

## Deployment

Vercel builds the frontend and runs the FastAPI app as a Python function from `api/index.py`. Vercel does not run the Docker image; Docker is for running locally or on any container host.

## AI tools used

Claude handled research, the spec, decisions, writing failing tests first, and review of every step. Codex wrote the implementation code against those tests. Deepak reviewed and traced each step.
