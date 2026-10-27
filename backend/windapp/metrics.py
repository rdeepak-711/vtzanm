"""Forecast error summary metrics."""

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class Summary:
    """Summary statistics for a collection of forecast errors."""

    n: int
    mae_mw: float | None
    bias_mw: float | None
    too_high: int | None
    share_too_high: float | None
    p90_mw: float | None
    max_error_mw: float | None
    min_error_mw: float | None


def p90(errors: list[float]) -> float:
    """Return the nearest-rank 90th percentile without sorting the input."""
    if not errors:
        raise ValueError("p90 requires at least one error")
    ordered = sorted(errors)
    return round(ordered[ceil(0.9 * len(ordered)) - 1], 1)


def summarise(errors: list[float]) -> Summary:
    """Calculate rounded accuracy metrics for forecast errors in MW."""
    n = len(errors)
    if n == 0:
        return Summary(0, None, None, None, None, None, None, None)

    too_high = sum(error > 0 for error in errors)
    return Summary(
        n=n,
        mae_mw=round(sum(abs(error) for error in errors) / n, 1),
        bias_mw=round(sum(errors) / n, 1),
        too_high=too_high,
        share_too_high=too_high / n,
        p90_mw=p90(errors),
        max_error_mw=round(max(errors), 1),
        min_error_mw=round(min(errors), 1),
    )
