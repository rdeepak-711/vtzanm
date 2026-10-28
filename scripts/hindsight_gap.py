"""How much better the forecast looks in hindsight than it was at decision time.

For every delivery hour, compare two forecasts against the same actual:
  - decision time: the run the buyer had at the auction cutoff (the app's rule)
  - hindsight: the newest run published before the hour started, which is what
    a "latest forecast vs actual" dashboard shows

Delivery days are 2-31 Jan only: the saved WINDFOR data stops at runs published
31 Jan 12:00, so 1 Feb's hindsight forecast would be cut short.

Run from the repo root: python3 scripts/hindsight_gap.py
"""

import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from windapp.actuals import hourly_actuals
from windapp.load import FUELHH_PATH, WINDFOR_PATH, load_fuelhh, load_windfor
from windapp.metrics import summarise
from windapp.pick import pick_day

FIRST_DAY = date(2026, 1, 2)
LAST_DAY = date(2026, 1, 31)


def main() -> None:
    forecasts = load_windfor(WINDFOR_PATH)
    actuals = hourly_actuals(load_fuelhh(FUELHH_PATH))

    # Newest run published at or before each hour's start.
    runs_by_start = defaultdict(list)
    for row in forecasts:
        if row.publish_time <= row.start_time:
            runs_by_start[row.start_time].append(row)
    hindsight = {start: max(rows, key=lambda r: r.publish_time) for start, rows in runs_by_start.items()}

    for cutoff in ("09:20", "09:50"):
        decision_errors, hindsight_errors, hindsight_leads = [], [], []
        day = FIRST_DAY
        while day <= LAST_DAY:
            for hour in pick_day(forecasts, day, cutoff):
                actual = actuals.get(hour.start_time)
                late = hindsight.get(hour.start_time)
                if hour.forecast_mw is None or actual is None or actual.actual_mw is None or late is None:
                    continue
                decision_errors.append(hour.forecast_mw - actual.actual_mw)
                hindsight_errors.append(late.generation_mw - actual.actual_mw)
                hindsight_leads.append((hour.start_time - late.publish_time).total_seconds() / 3600)
            day += timedelta(days=1)

        at_decision = summarise(decision_errors)
        in_hindsight = summarise(hindsight_errors)
        print(f"Cutoff {cutoff}, delivery 2-31 Jan, {at_decision.n} hours")
        print(f"  {'':22}{'decision time':>15}{'hindsight':>12}{'gap':>10}")
        for label, field in (("avg miss (MW)", "mae_mw"), ("lean (MW)", "bias_mw"), ("90% buffer (MW)", "p90_mw")):
            a, h = getattr(at_decision, field), getattr(in_hindsight, field)
            print(f"  {label:22}{a:>15,.1f}{h:>12,.1f}{a - h:>10,.1f}")
        print(f"  {'too high (hours)':22}{at_decision.too_high:>15}{in_hindsight.too_high:>12}")
        print(f"  hindsight run published {min(hindsight_leads):.1f}-{max(hindsight_leads):.1f} h before delivery")
        print(f"  the dashboard view understates the miss by {at_decision.mae_mw / in_hindsight.mae_mw:.1f}x")
        print()


if __name__ == "__main__":
    main()
