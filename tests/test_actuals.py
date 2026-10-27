"""Step 1C: hourly actuals. Spec rule 4 (spec/site.md), decision D4.

FUELHH gives one value per half hour. The actual for hour H is the mean of
the H:00 and H:30 slots; with one slot missing, use the other and flag it.
"""

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from windapp.actuals import HourActual, hourly_actuals
from windapp.load import ActualRow

UTC = timezone.utc
DATA = Path(__file__).resolve().parent.parent / "data" / "fuelhh_2026-01.json"


def at(day: int, hh: int, mm: int = 0, month: int = 1) -> datetime:
    return datetime(2026, month, day, hh, mm, tzinfo=UTC)


def slot(start: datetime, mw: int) -> ActualRow:
    return ActualRow(start_time=start, generation_mw=mw)


# --- one hour ------------------------------------------------------------------------


def test_hour_is_the_average_of_its_two_slots():
    result = hourly_actuals([slot(at(15, 12), 9_700), slot(at(15, 12, 30), 9_881)])
    assert result[at(15, 12)].actual_mw == 9_790.5
    assert result[at(15, 12)].partial is False


def test_result_is_keyed_by_the_hour_not_the_half_hour():
    result = hourly_actuals([slot(at(15, 12), 9_700), slot(at(15, 12, 30), 9_881)])
    assert list(result) == [at(15, 12)]
    assert result[at(15, 12)].start_time == at(15, 12)


def test_only_the_first_slot_uses_it_and_flags_partial():
    result = hourly_actuals([slot(at(15, 12), 9_700)])
    assert result[at(15, 12)].actual_mw == 9_700
    assert result[at(15, 12)].partial is True


def test_only_the_second_slot_uses_it_and_flags_partial():
    # The 12:30 slot still belongs to the 12:00 hour.
    result = hourly_actuals([slot(at(15, 12, 30), 9_881)])
    assert result[at(15, 12)].actual_mw == 9_881
    assert result[at(15, 12)].partial is True


def test_missing_slot_is_never_treated_as_zero():
    result = hourly_actuals([slot(at(15, 12), 9_700)])
    assert result[at(15, 12)].actual_mw != 4_850


def test_hour_with_no_slots_is_absent():
    # Both slots missing: the hour has no actual, so it isn't in the result at all.
    # The service layer turns a missing hour into actual_mw = null.
    result = hourly_actuals([slot(at(15, 11), 1), slot(at(15, 11, 30), 1)])
    assert at(15, 12) not in result


# --- many hours ------------------------------------------------------------------------


def test_several_hours_across_midnight():
    rows = [
        slot(at(15, 23), 100), slot(at(15, 23, 30), 200),
        slot(at(16, 0), 300), slot(at(16, 0, 30), 500),
    ]
    result = hourly_actuals(rows)
    assert result[at(15, 23)].actual_mw == 150
    assert result[at(16, 0)].actual_mw == 400


def test_input_order_does_not_matter():
    rows = [slot(at(15, 12, 30), 9_881), slot(at(15, 13), 1_000), slot(at(15, 12), 9_700)]
    result = hourly_actuals(rows)
    assert result[at(15, 12)].actual_mw == 9_790.5
    assert result[at(15, 13)].partial is True


def test_empty_input_gives_empty_result():
    assert hourly_actuals([]) == {}


def test_hour_actual_cannot_be_changed():
    result = hourly_actuals([slot(at(15, 12), 9_700), slot(at(15, 12, 30), 9_881)])
    with pytest.raises(dataclasses.FrozenInstanceError):
        result[at(15, 12)].actual_mw = 0


def test_hour_actual_fields():
    names = [f.name for f in dataclasses.fields(HourActual)]
    assert names == ["start_time", "actual_mw", "partial"]


# --- the real January file ---------------------------------------------------------------
# Parsed here with the standard library, so this step doesn't depend on step 1D's loader.


@pytest.fixture(scope="module")
def january() -> dict[datetime, HourActual]:
    raw = json.loads(DATA.read_text())
    rows = [
        slot(datetime.fromisoformat(r["startTime"].replace("Z", "+00:00")), r["generation"])
        for r in raw
        if r["fuelType"] == "WIND"
    ]
    return hourly_actuals(rows)


def test_real_january_has_744_hours(january):
    # 2 Jan 00:00 to 1 Feb 23:00
    assert len(january) == 744
    assert min(january) == at(2, 0)
    assert max(january) == at(1, 23, month=2)


def test_real_january_has_no_partial_hours(january):
    assert not any(h.partial for h in january.values())


def test_real_15_jan_values(january):
    assert january[at(15, 0)].actual_mw == 14_456.5
    assert january[at(15, 1)].actual_mw == 14_358.0
    assert january[at(15, 12)].actual_mw == 9_790.5
