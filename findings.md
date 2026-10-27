# Findings — Gridbricks wind forecast challenge

## Requirements (from the brief)

- Client: UK supplier, day-ahead buying team. App must (1) show the latest wind forecast available at decision time, (2) quantify forecast accuracy so decisions can account for the error.
- Data: Elexon FUELHH (fuelType WIND) and WINDFOR only. Purchase decisions made in January 2026.
- Stack: React front end, Python back end, Docker, deployed on Vercel or Heroku. AI use stated in README. Max 16 h.
- Deliverables: unlisted YouTube video ≤10 min (≤5 min client pitch + ≤5 min tech-lead walkthrough; evaluation starts with the video), public repo with random name + README (files/dirs, how to start, deploy link), submission form, all URLs checked in incognito.

## Research findings

### Elexon's own definitions (API spec, https://data.elexon.co.uk/swagger/v1/swagger.json, read 27 Oct 2026)

- **WINDFOR:** "wind generation forecast for wind farms which are visible to the ESO and have operational metering. Updated data is published by NGESO up to 8 times a day at 03:30, 05:30, 08:30, 10:30, 12:30, 16:30, 19:30 and 23:30." (ESO = the GB electricity system operator, formerly National Grid ESO, now NESO.)
- **FUELHH:** "half-hourly generation outturn (Generation By Fuel type) … for Great Britain. The data is aggregated by Fuel Type category and updated at 30-minute intervals with average MW values over 30 minutes for each category."
- **Elexon glossary (via search; page itself is behind a bot check):** fuel-type data is measured by National Grid from operational metering of generation connected to the high-voltage transmission system.
- **Older glossary text** says WINDFOR runs 4 times a day with 49 values. That is outdated: January 2026 data has 8 runs a day with 73 values each.

### What the data shows (January 2026, checked by script)

- WINDFOR publishTimes in January: 02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30, 22:30 UTC. All 8 runs present every day.
- Each run: 73 hourly rows, 21:00 the day before → 21:00 two days after.
- FUELHH: 48 slots a day, complete for 2 Jan – 1 Feb.
- Full month (744 delivery hours, 07:30 run vs on-the-hour actual): MAE 2,022 MW, bias +1,746 MW, forecast too high in 85% of hours, 90th-percentile shortfall 4,158 MW. Using the half-hour average: MAE 2,039 MW (under 1% different).
- **Under D4 (actual = average of the two half-hours), the numbers the tests must use:** month n=744, MAE 2,039, bias +1,748, too high 632/744, P90 4,098, worst +6,870, most negative −3,550, missed by ≥1,000 MW in 552 hours, 0 partial hours. 15 Jan: MAE 1,042, bias +1,042, 24/24 too high, worst +1,812, smallest +242. (The 2,022 / 1,746 / 4,158 / 1,025 figures elsewhere use the on-the-hour actual only.)

## Issues & open questions

1. **Coverage:** both datasets describe metered wind visible to the system operator, so both likely leave out small "embedded" wind farms on local networks. A coverage mismatch is therefore *less* likely to explain the bias than first thought. Not proven: neither text lists the exact set of wind farms.
2. **Curtailment (hypothesis, not verified):** FUELHH is what wind farms actually delivered, including when they were paid to turn down because the grid was full. If WINDFOR forecasts what the wind could produce, every turn-down shows up as "forecast too high". The brief allows no other data, so this can't be measured here. State it in the video as a likely part of the bias.
3. **Publish-time mismatch (unresolved):** the docs say runs publish at 03:30, 05:30, 08:30 …, but January's `publishTime` values are an hour earlier (02:30, 04:30, 07:30 …). Most likely the docs quote UK summer time (BST = UTC+1) while the data is in UTC. If instead runs really become available an hour after `publishTime`, then the 09:30 run would miss the N2EX 09:50 deadline. The 07:30 run is safe before 09:20 either way, so the default result is unaffected.

## Resources

- Elexon API spec: https://data.elexon.co.uk/swagger/v1/swagger.json
- FUELHH stream: https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream
- WINDFOR stream: https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream
- Elexon glossary, Wind Generation Forecast: https://www.elexon.co.uk/bsc/glossary/wind-generation-forecast/
- Elexon glossary, Half Hourly Generation by Fuel Type: https://www.elexon.co.uk/bsc/glossary/half-hourly-generation-by-fuel-type/
- Nord Pool GB day-ahead auction (09:50 gate): https://support.nordpoolgroup.com/support/solutions/articles/8000088463-about-the-day-ahead-gb-auction
