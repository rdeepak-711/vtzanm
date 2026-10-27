"""Hourly actual generation from half-hour FUELHH rows."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from windapp.load import ActualRow


@dataclass(frozen=True)
class HourActual:
    """Actual generation for one hour."""

    start_time: datetime
    actual_mw: float | None
    partial: bool


def hourly_actuals(rows: list[ActualRow]) -> dict[datetime, HourActual]:
    """Average the available half-hour actuals for each hour."""
    slots_by_hour: dict[datetime, list[int]] = defaultdict(list)
    for row in rows:
        hour_start = row.start_time.replace(minute=0)
        slots_by_hour[hour_start].append(row.generation_mw)

    return {
        hour_start: HourActual(
            start_time=hour_start,
            actual_mw=sum(generations) / len(generations),
            partial=len(generations) == 1,
        )
        for hour_start, generations in sorted(slots_by_hour.items())
    }
