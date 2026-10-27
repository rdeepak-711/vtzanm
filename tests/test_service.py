"""Step 3: the service. Spec rules 1-7, 'Expected numbers', and the /api/day and
/api/month body shapes. This is where 1A-1D are joined and the real January
numbers come out.
"""

import json
from datetime import date

import pytest

from windapp.service import DELIVERY_FROM, DELIVERY_TO, day_view, month_view

MW = dict(abs=0.1)  # values are rounded to 1 decimal

SUMMARY_FIELDS = ["n", "mae_mw", "bias_mw", "too_high", "share_too_high",
                  "p90_mw", "max_error_mw", "min_error_mw"]


@pytest.fixture(scope="module")
def jan15():
    return day_view(date(2026, 1, 15), "09:20")


@pytest.fixture(scope="module")
def month():
    return month_view("09:20")


@pytest.fixture(scope="module")
def month_0950():
    return month_view("09:50")


# --- the delivery window and the guards ---------------------------------------------------


def test_delivery_window_is_2_jan_to_1_feb():
    assert DELIVERY_FROM == date(2026, 1, 2)
    assert DELIVERY_TO == date(2026, 2, 1)


@pytest.mark.parametrize("day", [date(2026, 1, 1), date(2026, 2, 2), date(2025, 12, 31)])
def test_day_outside_the_window_is_refused(day):
    with pytest.raises(ValueError, match="2026-01-02"):
        day_view(day, "09:20")


def test_unknown_cutoff_is_refused_for_a_day():
    with pytest.raises(ValueError):
        day_view(date(2026, 1, 15), "10:00")


def test_unknown_cutoff_is_refused_for_the_month():
    with pytest.raises(ValueError):
        month_view("10:00")


def test_both_ends_of_the_window_work():
    assert len(day_view(date(2026, 1, 2), "09:20")["hours"]) == 24
    assert len(day_view(date(2026, 2, 1), "09:20")["hours"]) == 24


def test_cutoff_defaults_to_0920():
    assert day_view(date(2026, 1, 15))["cutoff"] == "09:20"
    assert month_view()["cutoff"] == "09:20"


# --- day view: 15 Jan ------------------------------------------------------------------------


def test_day_header(jan15):
    assert jan15["date"] == "2026-01-15"
    assert jan15["cutoff"] == "09:20"
    assert jan15["decision_time"] == "2026-01-14T09:20:00Z"
    assert jan15["runs_used"] == ["2026-01-14T07:30:00Z"]


def test_day_has_24_hours_in_order(jan15):
    starts = [h["start"] for h in jan15["hours"]]
    assert starts == [f"2026-01-15T{h:02d}:00:00Z" for h in range(24)]


def test_day_hour_fields(jan15):
    assert list(jan15["hours"][0]) == ["start", "forecast_mw", "actual_mw", "error_mw",
                                       "run_published", "lead_hours", "partial"]


@pytest.mark.parametrize("h, forecast, actual, error", [
    (0, 15_834, 14_456.5, 1_377.5),
    (1, 15_478, 14_358.0, 1_120.0),
    (12, 11_049, 9_790.5, 1_258.5),
])
def test_day_hour_values(jan15, h, forecast, actual, error):
    hour = jan15["hours"][h]
    assert hour["forecast_mw"] == forecast
    assert hour["actual_mw"] == pytest.approx(actual, **MW)
    assert hour["error_mw"] == pytest.approx(error, **MW)
    assert hour["run_published"] == "2026-01-14T07:30:00Z"
    assert hour["partial"] is False


def test_day_lead_hours(jan15):
    assert jan15["hours"][0]["lead_hours"] == 16.5
    assert jan15["hours"][12]["lead_hours"] == 28.5
    assert jan15["hours"][23]["lead_hours"] == 39.5


def test_day_summary(jan15):
    s = jan15["summary"]
    assert list(s) == SUMMARY_FIELDS
    assert s["n"] == 24
    assert s["mae_mw"] == pytest.approx(1041.8, **MW)
    assert s["bias_mw"] == pytest.approx(1041.8, **MW)  # every hour too high: lean = avg miss
    assert s["too_high"] == 24
    assert s["share_too_high"] == 1.0
    assert s["p90_mw"] == pytest.approx(1633.5, **MW)
    assert s["max_error_mw"] == pytest.approx(1812.5, **MW)
    assert s["min_error_mw"] == pytest.approx(242.0, **MW)


def test_0950_day_uses_the_0930_run():
    day = day_view(date(2026, 1, 15), "09:50")
    assert day["decision_time"] == "2026-01-14T09:50:00Z"
    assert day["runs_used"] == ["2026-01-14T09:30:00Z"]


def test_day_view_is_plain_json():
    json.dumps(day_view(date(2026, 1, 15), "09:20"))


# --- month view: 09:20 -----------------------------------------------------------------------


def test_month_header(month):
    assert month["cutoff"] == "09:20"
    assert month["from"] == "2026-01-02"
    assert month["to"] == "2026-02-01"


def test_month_summary(month):
    s = month["summary"]
    assert list(s) == SUMMARY_FIELDS
    assert s["n"] == 744
    assert s["mae_mw"] == pytest.approx(2038.9, **MW)
    assert s["bias_mw"] == pytest.approx(1747.9, **MW)
    assert s["too_high"] == 632
    assert s["p90_mw"] == pytest.approx(4098.5, **MW)
    assert s["max_error_mw"] == pytest.approx(6870.0, **MW)
    assert s["min_error_mw"] == pytest.approx(-3550.0, **MW)


def test_month_counts(month):
    assert month["hours_off_by_1000"] == 552
    assert month["partial_hours"] == 0


def test_month_by_hour_of_day(month):
    rows = month["by_hour_of_day"]
    assert [r["hour"] for r in rows] == list(range(24))
    assert all(r["n"] == 31 for r in rows)
    assert rows[0]["mae_mw"] == pytest.approx(2027.8, **MW)
    assert rows[0]["bias_mw"] == pytest.approx(1952.7, **MW)
    assert rows[0]["too_high"] == 29
    assert rows[0]["p90_mw"] == pytest.approx(3937.0, **MW)
    assert rows[12]["mae_mw"] == pytest.approx(1929.3, **MW)
    assert rows[12]["bias_mw"] == pytest.approx(1387.7, **MW)
    assert rows[12]["too_high"] == 24


def test_month_by_day(month):
    rows = month["by_day"]
    assert len(rows) == 31
    assert rows[0]["date"] == "2026-01-02"
    assert rows[-1]["date"] == "2026-02-01"
    assert all(r["n"] == 24 for r in rows)
    assert all(r["runs_used"] for r in rows)


def test_month_worst_and_best_days(month):
    by_mae = sorted(month["by_day"], key=lambda r: r["mae_mw"], reverse=True)
    assert [r["date"] for r in by_mae[:3]] == ["2026-01-28", "2026-01-12", "2026-01-11"]
    assert by_mae[0]["mae_mw"] == pytest.approx(5374.8, **MW)
    assert by_mae[-1]["date"] == "2026-01-19"
    assert by_mae[-1]["mae_mw"] == pytest.approx(736.1, **MW)


def test_month_15_jan_matches_the_day_view(month, jan15):
    row = next(r for r in month["by_day"] if r["date"] == "2026-01-15")
    assert row["mae_mw"] == jan15["summary"]["mae_mw"]


def test_month_view_is_plain_json(month):
    json.dumps(month)


# --- month view: 09:50 -----------------------------------------------------------------------


def test_month_summary_0950(month_0950):
    s = month_0950["summary"]
    assert s["n"] == 744
    assert s["mae_mw"] == pytest.approx(2013.0, **MW)
    assert s["bias_mw"] == pytest.approx(1729.9, **MW)
    assert s["too_high"] == 627
    assert s["p90_mw"] == pytest.approx(4145.5, **MW)
    assert s["max_error_mw"] == pytest.approx(6833.0, **MW)
    assert s["min_error_mw"] == pytest.approx(-4128.0, **MW)


# --- caching -----------------------------------------------------------------------------------


def test_month_is_computed_once():
    assert month_view("09:20") is month_view("09:20")


def test_day_is_computed_once():
    assert day_view(date(2026, 1, 15), "09:20") is day_view(date(2026, 1, 15), "09:20")
