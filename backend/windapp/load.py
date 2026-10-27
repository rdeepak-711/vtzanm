"""Typed rows used by the wind data pipeline."""

from dataclasses import dataclass
from datetime import datetime


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
