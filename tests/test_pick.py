"""Step 1B: the pick rule. Spec rules 2 and 3 (spec/site.md), decisions D2 and D3.

For each delivery hour: keep runs published at or before the decision time
(D-1 at the cutoff), take the newest. Never use a run published later.
"""

import dataclasses
import json
from datetime import date, datetime, time, timezone
from pathlib import Path

import pytest

from windapp.load import ForecastRow
from windapp.pick import CUTOFFS, PickedHour, decision_time, pick_day

UTC = timezone.utc
DATA = Path(__file__).resolve().parent.parent / "data" / "windfor_2026-01.json"


def at(day: int, hh: int, mm: int = 0, month: int = 1) -> datetime:
    return datetime(2026, month, day, hh, mm, tzinfo=UTC)


def row(published: datetime, start: datetime, mw: int) -> ForecastRow:
    return ForecastRow(publish_time=published, start_time=start, generation_mw=mw)


def hour(picked: list[PickedHour], h: int) -> PickedHour:
    return picked[h]


# --- decision time --------------------------------------------------------------


def test_cutoffs_are_the_two_auction_closes():
    assert CUTOFFS == {"09:20": time(9, 20), "09:50": time(9, 50)}


def test_decision_time_is_the_day_before_at_0920():
    assert decision_time(date(2026, 1, 15), "09:20") == at(14, 9, 20)


def test_decision_time_at_0950():
    assert decision_time(date(2026, 1, 15), "09:50") == at(14, 9, 50)


def test_decision_time_crosses_the_month():
    # Delivery 1 Feb is decided on 31 Jan.
    assert decision_time(date(2026, 2, 1), "09:20") == at(31, 9, 20)


def test_decision_time_is_utc_aware():
    assert decision_time(date(2026, 1, 15), "09:20").tzinfo is not None


def test_unknown_cutoff_is_rejected():
    with pytest.raises(ValueError):
        decision_time(date(2026, 1, 15), "10:00")


# --- the pick rule on hand-made runs ------------------------------------------------

# Three runs on 14 Jan, all predicting 15 Jan 12:00.
NOON = at(15, 12)
RUNS_14_JAN = [
    row(at(14, 4, 30), NOON, 10_700),
    row(at(14, 7, 30), NOON, 11_049),
    row(at(14, 9, 30), NOON, 10_900),
]


def test_returns_24_hours_in_order():
    picked = pick_day(RUNS_14_JAN, date(2026, 1, 15), "09:20")
    assert len(picked) == 24
    assert [p.start_time for p in picked] == [at(15, h) for h in range(24)]


def test_0920_takes_the_newest_run_before_the_cutoff():
    p = hour(pick_day(RUNS_14_JAN, date(2026, 1, 15), "09:20"), 12)
    assert p.forecast_mw == 11_049
    assert p.run_published == at(14, 7, 30)


def test_0950_lets_the_0930_run_in():
    p = hour(pick_day(RUNS_14_JAN, date(2026, 1, 15), "09:50"), 12)
    assert p.forecast_mw == 10_900
    assert p.run_published == at(14, 9, 30)


def test_run_published_after_the_cutoff_is_never_used():
    # Only a later run exists: the hour has no forecast rather than a hindsight one.
    rows = [row(at(14, 11, 30), NOON, 9_999), row(at(15, 7, 30), NOON, 9_900)]
    p = hour(pick_day(rows, date(2026, 1, 15), "09:20"), 12)
    assert p.forecast_mw is None


def test_run_published_exactly_at_the_cutoff_counts():
    rows = [row(at(14, 7, 30), NOON, 11_049), row(at(14, 9, 20), NOON, 10_500)]
    p = hour(pick_day(rows, date(2026, 1, 15), "09:20"), 12)
    assert p.forecast_mw == 10_500


def test_missing_run_falls_back_to_the_older_one():
    # No 07:30 run: the 04:30 run is the newest one left.
    rows = [row(at(14, 4, 30), NOON, 10_700), row(at(14, 9, 30), NOON, 10_900)]
    p = hour(pick_day(rows, date(2026, 1, 15), "09:20"), 12)
    assert p.forecast_mw == 10_700
    assert p.run_published == at(14, 4, 30)
    assert p.lead_hours == 31.5


def test_input_order_does_not_matter():
    shuffled = [RUNS_14_JAN[2], RUNS_14_JAN[0], RUNS_14_JAN[1]]
    p = hour(pick_day(shuffled, date(2026, 1, 15), "09:20"), 12)
    assert p.forecast_mw == 11_049


def test_rows_for_other_days_are_ignored():
    rows = RUNS_14_JAN + [row(at(14, 7, 30), at(16, 12), 5_000)]
    picked = pick_day(rows, date(2026, 1, 15), "09:20")
    assert len(picked) == 24
    assert hour(picked, 12).forecast_mw == 11_049


def test_hour_without_any_forecast_is_blank_not_a_crash():
    p = hour(pick_day(RUNS_14_JAN, date(2026, 1, 15), "09:20"), 3)
    assert p.start_time == at(15, 3)
    assert p.forecast_mw is None
    assert p.run_published is None
    assert p.lead_hours is None


# --- lead time --------------------------------------------------------------------


def test_lead_hours_from_the_0730_run():
    run = at(14, 7, 30)
    rows = [row(run, at(15, h), 10_000 + h) for h in range(24)]
    picked = pick_day(rows, date(2026, 1, 15), "09:20")
    assert hour(picked, 0).lead_hours == 16.5
    assert hour(picked, 12).lead_hours == 28.5
    assert hour(picked, 23).lead_hours == 39.5


def test_picked_hour_cannot_be_changed():
    p = hour(pick_day(RUNS_14_JAN, date(2026, 1, 15), "09:20"), 12)
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.forecast_mw = 0


# --- the real January file ------------------------------------------------------------
# Parsed here with the standard library, so this step doesn't depend on step 1D's loader.


@pytest.fixture(scope="module")
def january() -> list[ForecastRow]:
    raw = json.loads(DATA.read_text())
    return [
        row(
            datetime.fromisoformat(r["publishTime"].replace("Z", "+00:00")),
            datetime.fromisoformat(r["startTime"].replace("Z", "+00:00")),
            r["generation"],
        )
        for r in raw
    ]


def test_real_15_jan_uses_the_14_jan_0730_run_every_hour(january):
    picked = pick_day(january, date(2026, 1, 15), "09:20")
    assert {p.run_published for p in picked} == {at(14, 7, 30)}


def test_real_15_jan_forecast_values(january):
    picked = pick_day(january, date(2026, 1, 15), "09:20")
    assert hour(picked, 0).forecast_mw == 15_834
    assert hour(picked, 1).forecast_mw == 15_478
    assert hour(picked, 12).forecast_mw == 11_049


def test_real_15_jan_at_0950_uses_the_0930_run(january):
    picked = pick_day(january, date(2026, 1, 15), "09:50")
    assert {p.run_published for p in picked} == {at(14, 9, 30)}


def test_real_1_feb_is_decided_on_31_jan(january):
    picked = pick_day(january, date(2026, 2, 1), "09:20")
    assert {p.run_published for p in picked} == {at(31, 7, 30)}
    assert all(p.forecast_mw is not None for p in picked)
