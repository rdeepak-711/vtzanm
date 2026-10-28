"""Cached service views for wind forecast accuracy."""

from dataclasses import asdict
from datetime import date, datetime, timedelta
from functools import lru_cache

from windapp.actuals import HourActual, hourly_actuals
from windapp.load import FUELHH_PATH, WINDFOR_PATH, ActualRow, ForecastRow, load_fuelhh, load_windfor
from windapp.metrics import summarise
from windapp.pick import CUTOFFS, decision_time, pick_day

DELIVERY_FROM = date(2026, 1, 2)
DELIVERY_TO = date(2026, 2, 1)


@lru_cache(maxsize=1)
def _source_data() -> tuple[list[ForecastRow], dict[datetime, HourActual]]:
    """Load forecasts and aggregated actuals once per process."""
    forecasts = load_windfor(WINDFOR_PATH)
    actual_rows: list[ActualRow] = load_fuelhh(FUELHH_PATH)
    return forecasts, hourly_actuals(actual_rows)


def _iso_utc(value: datetime) -> str:
    """Format a UTC datetime with the API's trailing Z."""
    return value.isoformat().replace("+00:00", "Z")


def _validate_cutoff(cutoff: str) -> None:
    if cutoff not in CUTOFFS:
        raise ValueError(f"Unknown cutoff {cutoff!r}; allowed cutoffs are 09:20 and 09:50")


def _errors(hours: list[dict]) -> list[float]:
    return [hour["error_mw"] for hour in hours if hour["error_mw"] is not None]


@lru_cache(maxsize=None)
def day_view(delivery_day: date, cutoff: str = "09:20") -> dict:
    """Return the forecast, actual, and error view for one delivery day."""
    _validate_cutoff(cutoff)
    if not DELIVERY_FROM <= delivery_day <= DELIVERY_TO:
        raise ValueError(
            f"Delivery day must be in the allowed range {DELIVERY_FROM.isoformat()} to {DELIVERY_TO.isoformat()}"
        )

    forecasts, actuals = _source_data()
    picked_hours = pick_day(forecasts, delivery_day, cutoff)
    hours = []
    for picked in picked_hours:
        actual = actuals.get(picked.start_time)
        actual_mw = actual.actual_mw if actual else None
        error_mw = (
            round(picked.forecast_mw - actual_mw, 1)
            if picked.forecast_mw is not None and actual_mw is not None
            else None
        )
        hours.append(
            {
                "start": _iso_utc(picked.start_time),
                "forecast_mw": picked.forecast_mw,
                "actual_mw": actual_mw,
                "error_mw": error_mw,
                "run_published": _iso_utc(picked.run_published) if picked.run_published else None,
                "lead_hours": picked.lead_hours,
                "partial": actual.partial if actual else False,
            }
        )

    return {
        "date": delivery_day.isoformat(),
        "cutoff": cutoff,
        "decision_time": _iso_utc(decision_time(delivery_day, cutoff)),
        "runs_used": sorted({hour["run_published"] for hour in hours if hour["run_published"]}),
        "hours": hours,
        "summary": asdict(summarise(_errors(hours))),
    }


@lru_cache(maxsize=None)
def month_view(cutoff: str = "09:20") -> dict:
    """Return aggregate forecast accuracy for the full delivery window."""
    _validate_cutoff(cutoff)
    days = [
        day_view(DELIVERY_FROM + timedelta(days=offset), cutoff)
        for offset in range((DELIVERY_TO - DELIVERY_FROM).days + 1)
    ]
    all_hours = [hour for day in days for hour in day["hours"]]
    errors = _errors(all_hours)
    by_hour = []
    for hour_number in range(24):
        hour_errors = [
            hour["error_mw"]
            for hour in all_hours
            if datetime.fromisoformat(hour["start"].replace("Z", "+00:00")).hour == hour_number
            and hour["error_mw"] is not None
        ]
        by_hour.append({"hour": hour_number, **asdict(summarise(hour_errors))})

    by_day = []
    for day in days:
        by_day.append(
            {
                "date": day["date"],
                **day["summary"],
                "runs_used": day["runs_used"],
            }
        )

    return {
        "cutoff": cutoff,
        "from": DELIVERY_FROM.isoformat(),
        "to": DELIVERY_TO.isoformat(),
        "summary": asdict(summarise(errors)),
        "hours_off_by_1000": sum(abs(error) >= 1000 for error in errors),
        "partial_hours": sum(hour["partial"] for hour in all_hours),
        "by_hour_of_day": by_hour,
        "by_day": by_day,
    }
