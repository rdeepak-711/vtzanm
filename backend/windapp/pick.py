"""Select the latest eligible forecast for each delivery hour."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from windapp.load import ForecastRow

CUTOFFS = {"09:20": time(9, 20), "09:50": time(9, 50)}


@dataclass(frozen=True)
class PickedHour:
    """Forecast selected for one hour, or empty when none qualifies."""

    start_time: datetime
    forecast_mw: int | None
    run_published: datetime | None
    lead_hours: float | None


def decision_time(delivery_day: date, cutoff: str) -> datetime:
    """Return the UTC decision time on the day before delivery."""
    if cutoff not in CUTOFFS:
        raise ValueError(f"Unknown cutoff: {cutoff}")
    previous_day = delivery_day - timedelta(days=1)
    return datetime.combine(previous_day, CUTOFFS[cutoff], tzinfo=timezone.utc)


def pick_day(rows: list[ForecastRow], delivery_day: date, cutoff: str) -> list[PickedHour]:
    """Pick the newest eligible forecast for each hour of a delivery day."""
    cutoff_time = decision_time(delivery_day, cutoff)
    by_start: dict[datetime, list[ForecastRow]] = defaultdict(list)
    for row in rows:
        by_start[row.start_time].append(row)

    picked = []
    for hour in range(24):
        start_time = datetime.combine(delivery_day, time(hour), tzinfo=timezone.utc)
        eligible = [
            row
            for row in by_start.get(start_time, [])
            if row.start_time >= row.publish_time and row.publish_time <= cutoff_time
        ]
        if not eligible:
            picked.append(PickedHour(start_time, None, None, None))
            continue

        latest = max(eligible, key=lambda row: row.publish_time)
        lead = (start_time - latest.publish_time).total_seconds() / 3600
        picked.append(
            PickedHour(start_time, latest.generation_mw, latest.publish_time, round(lead, 1))
        )
    return picked
