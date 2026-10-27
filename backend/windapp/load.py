"""Typed rows used by the wind data pipeline."""

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


DATA_DIR: Path = Path(__file__).resolve().parents[2] / "data"
WINDFOR_PATH = DATA_DIR / "windfor_2026-01.json"
FUELHH_PATH = DATA_DIR / "fuelhh_2026-01.json"


def _parse_utc(value: str) -> datetime:
    """Parse an ISO timestamp ending in Z as a UTC-aware datetime."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp has no timezone information: {value!r}")
    return parsed


@dataclass(frozen=True)
class ForecastRow:
    """One published wind forecast for a delivery hour."""

    publish_time: datetime
    start_time: datetime
    generation_mw: int


@dataclass(frozen=True)
class ActualRow:
    """One measured wind generation interval."""

    start_time: datetime
    generation_mw: int


def load_windfor(path: Path) -> list[ForecastRow]:
    """Load forecast rows from a saved WINDFOR JSON file."""
    with path.open() as file:
        rows = json.load(file)
    return [
        ForecastRow(
            publish_time=_parse_utc(row["publishTime"]),
            start_time=_parse_utc(row["startTime"]),
            generation_mw=int(row["generation"]),
        )
        for row in rows
    ]


def load_fuelhh(path: Path) -> list[ActualRow]:
    """Load WIND actual rows from a saved FUELHH JSON file."""
    with path.open() as file:
        rows = json.load(file)
    return [
        ActualRow(
            start_time=_parse_utc(row["startTime"]),
            generation_mw=int(row["generation"]),
        )
        for row in rows
        if row["fuelType"] == "WIND"
    ]
