# Decisions

Each entry: date · what was decided · what else was considered · why this won · what it costs. Superseded entries stay, marked reversed with a date.

## D1 · Delivery days are 2 Jan – 1 Feb 2026 (744 hours)

- **Date:** 27 Oct 2026
- **Decided:** the app covers buying decisions made on 1–31 January 2026. Each decision on day D-1 buys power for day D, so the delivery days are 2 Jan to 1 Feb.
- **Considered:** delivery days 1–31 Jan. That would include 1 Jan, whose decision was made on 31 Dec (outside January), and drop 1 Feb, whose decision was made on 31 Jan (inside January).
- **Why:** the brief says "purchase decisions made in January 2026". The decision day is what matters, not the delivery day.
- **Cost:** needs FUELHH actuals for 1 Feb, and the date range in the app looks odd at first glance, so the screen and README must say why it ends on 1 Feb.

## D2 · Cutoff is 09:20 UK time on D-1 by default, with a 09:50 option

- **Date:** 27 Oct 2026
- **Decided:** the default decision time is 09:20 UK on the day before delivery, which is when the EPEX GB day-ahead auction closes. A switch changes it to 09:50, when the Nord Pool N2EX auction closes. In January UK time equals UTC, so no time-zone conversion is needed for this data.
- **Considered:** a single fixed cutoff; a free time picker; midnight of D-1.
- **Why:** these are the two real auction deadlines a GB day-ahead buyer faces. A free picker invites cutoffs no auction uses, and midnight is a guess with no market behind it.
- **Cost:** two result sets to compute and test. With 09:50 the 09:30 forecast run counts, but Elexon's docs list publish times an hour later than the data shows (03:30… vs 02:30…), most likely BST in the docs vs UTC in the data. If the docs are right literally, the 09:30 run would not be available by 09:50. The 09:20 default uses the 07:30 run and is safe either way. Recorded as an open issue in findings.md.

## D3 · For each delivery hour, use the newest forecast published at or before the cutoff, ignoring rows for hours already past

- **Date:** 27 Oct 2026
- **Decided:** for delivery hour H on day D, take every WINDFOR row with startTime = H and publishTime ≤ cutoff(D-1), drop rows where startTime < publishTime, and keep the one with the latest publishTime. In January 2026 at 09:20 this is always the 07:30 run of D-1.
- **Considered:** the forecast made closest to delivery (uses information the buyer did not have); the average of all runs before the cutoff; a fixed lead time such as "24 hours ahead".
- **Why:** the brief asks for the latest forecast available at decision time. Anything published after the cutoff is hindsight. Rows with startTime before publishTime are copies of past hours carried in each run and are not forecasts.
- **Cost:** lead time varies with the hour of day, from 16.5 h (00:00) to 39.5 h (23:00), so "error by hour of day" and "error by lead time" are the same thing in this app and can't be separated. If a run is missing, the hour falls back to an older run with a longer lead time; January had no missing runs, but the code must handle it and the screen must show which run was used.

## D4 · "Actual" for an hour is the average of its two half-hour FUELHH readings

- **Date:** 27 Oct 2026
- **Decided:** actual wind for hour H = mean of the FUELHH WIND values for the slots starting at H:00 and H:30.
- **Considered:** using only the H:00 slot.
- **Why:** FUELHH values are average MW over 30 minutes; averaging both slots covers the whole hour the forecast describes. Checked on January: MAE 2,039 MW vs 2,022 MW with the H:00 slot only, under 1% different, so the choice doesn't change any conclusion.
- **Cost:** if one half-hour is missing, the hour is either dropped or uses the single slot. Rule: use the slot that exists and mark the hour as partial; drop the hour only if both are missing.

## D5 · Accuracy is shown as three numbers plus error by hour of day

- **Date:** 27 Oct 2026
- **Decided:** error = forecast − actual (positive = forecast too high = buyer ends up short). Show: average miss (MAE), lean (mean signed error, "bias"), and the 90th-percentile shortfall (the 90% buffer: the MW of cover that would have covered 9 hours in 10). Also show these by hour of day, and the share of hours the forecast was too high.
- **Considered:** RMSE; MAPE (percentage error); a full error histogram only.
- **Why:** each number answers a buyer question. MAE: how wrong is it usually? Bias: which way does it lean? P90: how much extra cover do I hold to be safe most of the time? RMSE has no plain-English meaning for a buyer, and MAPE breaks down on calm hours when actual wind is near zero.
- **Cost:** the P90 buffer from one month (744 hours) is a rough number, and January is windy, so it should not be presented as valid for other months.

## D6 · January data is downloaded once, saved in the repo, with a script to re-download

- **Date:** 27 Oct 2026
- **Decided:** a Python script pulls FUELHH (fuelType=WIND) and WINDFOR for the January window from the Elexon API and saves them as JSON files in the repo. The app reads those files. No live API calls at page load.
- **Considered:** calling Elexon live on every request; a database.
- **Why:** the data for January 2026 is fixed history. Live calls would make the demo depend on Elexon being up and fast, and add latency for no gain. A database is extra setup for a few thousand rows. The script shows exactly where the numbers come from and lets a reviewer reproduce them.
- **Cost:** the app does not show newer days unless the script is rerun. Fine for this brief, which is about January.

## D7 · Stack: Python FastAPI back end, React (Vite) front end, Docker locally, Vercel deploy

- **Date:** 27 Oct 2026
- **Decided:** FastAPI serves the computed results as JSON; a Vite + React app shows them. `docker compose up` runs both locally. Production is on Vercel: the React build as static files, the FastAPI app as a Vercel Python function.
- **Considered:** Flask; Next.js; Heroku with the Docker image.
- **Why:** the brief requires React, Python and Docker, and allows Vercel or Heroku. FastAPI gives typed responses and auto API docs for little code. Vercel is already set up and free; Heroku has no free tier.
- **Cost:** on Vercel the Docker image is not what runs, since Vercel runs Python as a serverless function. Docker covers the local run only, and the README must say so plainly. Two run paths (Docker and Vercel) means two ways to break; both get checked before submission.

## D8 · Two screens only

- **Date:** 27 Oct 2026
- **Decided:** Screen 1: pick a delivery day; see the forecast the buyer had at the cutoff vs what actually came, hour by hour, with which run was used. Screen 2: the accuracy numbers from D5 for the month, by hour of day, with the worst days.
- **Considered:** a map; per-region views; a forecast-run comparison explorer; login.
- **Why:** these are the brief's two asks, one screen each. The data is national, so a map adds nothing. Extra screens cost hours that the video needs.
- **Cost:** a reviewer looking for flair sees a plain app. The video carries the story instead.

## D9 · No "how much to buy" calculator unless time is left over

- **Date:** 27 Oct 2026
- **Decided:** the app does not output a buy quantity. Optional, last: an input box where the buyer types their expected demand, and the app shows demand − (forecast − bias) and the same plus the P90 buffer.
- **Considered:** building the calculator as a core feature.
- **Why:** the allowed data has no demand figures, so any buy number would rest on a value the app makes up. The brief asks for the forecast and its accuracy, not a trading recommendation.
- **Cost:** the client pitch has to draw the line from "here is the error" to "here is what you do with it" in words rather than in the product.

## D10 · The switch-off (curtailment) explanation goes in the video as a likely cause, in one sentence

- **Date:** 27 Oct 2026
- **Decided:** in January the forecast was too high in 85% of hours (bias +1,746 MW). The video says part of this gap is likely wind farms being paid to turn down when the grid is full: WINDFOR most likely forecasts what the wind could make, while FUELHH records what was delivered. It is stated as a likely cause, not a finding.
- **Considered:** presenting the gap as pure forecast error; pulling Elexon's curtailment data to measure it.
- **Why:** the reviewers know GB wind. Calling the whole gap forecast error would look naive, and the brief allows only FUELHH and WINDFOR, so the cause can't be measured here. Either way the buyer doesn't receive switched-off power, so the advice (correct for the lean, hold the buffer) stands.
- **Cost:** one claim in the video rests on domain reasoning, not on this app's data. It must be worded as "likely", never as a measured result.

## D11 · The public repo excludes the learning pages and the brief PDF

- **Date:** 27 Oct 2026
- **Decided:** `.gitignore` keeps `docs/learn/` and `docs/*.pdf` out of the repo. The public repo holds the app, the data files, the spec, the tests, `docs/decisions.md`, `docs/flow.md`, `docs/mental-model.md`, `findings.md` and the README.
- **Considered:** publishing everything.
- **Why:** the learning pages mention people, other interviews and dates that have nothing to do with the app, and the brief is Gridbricks' document, not ours to republish. The decisions log and findings carry the reasoning a reviewer needs.
- **Cost:** a reviewer doesn't see the learning trail. The video's tech-lead part covers it instead.
