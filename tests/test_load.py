"""Step 1D: reading the saved Elexon files. Spec 'The data' and windapp.load exports.

Text times become UTC-aware datetimes; FUELHH keeps WIND rows only.
"""

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from windapp.load import (
    DATA_DIR,
    FUELHH_PATH,
    WINDFOR_PATH,
    ActualRow,
    ForecastRow,
    load_fuelhh,
    load_windfor,
)

UTC = timezone.utc
REPO = Path(__file__).resolve().parent.parent


def write(tmp_path: Path, name: str, rows: list[dict]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(rows))
    return path


WINDFOR_LINE = {
    "dataset": "WINDFOR",
    "publishTime": "2026-01-14T07:30:00Z",
    "startTime": "2026-01-15T12:00:00Z",
    "generation": 11049,
}


def fuelhh_line(start: str, fuel: str, mw: int) -> dict:
    return {
        "dataset": "FUELHH",
        "publishTime": "2026-01-15T12:30:00Z",
        "startTime": start,
        "settlementDate": "2026-01-15",
        "settlementPeriod": 25,
        "fuelType": fuel,
        "generation": mw,
    }


# --- WINDFOR ---------------------------------------------------------------------------


def test_windfor_line_becomes_a_forecast_row(tmp_path):
    rows = load_windfor(write(tmp_path, "wf.json", [WINDFOR_LINE]))
    assert rows == [
        ForecastRow(
            publish_time=datetime(2026, 1, 14, 7, 30, tzinfo=UTC),
            start_time=datetime(2026, 1, 15, 12, tzinfo=UTC),
            generation_mw=11049,
        )
    ]


def test_windfor_times_carry_utc(tmp_path):
    row = load_windfor(write(tmp_path, "wf.json", [WINDFOR_LINE]))[0]
    for t in (row.publish_time, row.start_time):
        assert t.tzinfo is not None
        assert t.utcoffset() == timedelta(0)


def test_windfor_generation_is_an_integer(tmp_path):
    row = load_windfor(write(tmp_path, "wf.json", [WINDFOR_LINE]))[0]
    assert isinstance(row.generation_mw, int)


def test_empty_windfor_file_gives_no_rows(tmp_path):
    assert load_windfor(write(tmp_path, "wf.json", [])) == []


# --- FUELHH ------------------------------------------------------------------------------


def test_fuelhh_keeps_wind_and_drops_other_fuels(tmp_path):
    lines = [
        fuelhh_line("2026-01-15T12:00:00Z", "WIND", 9742),
        fuelhh_line("2026-01-15T12:00:00Z", "CCGT", 8000),
        fuelhh_line("2026-01-15T12:30:00Z", "WIND", 9839),
        fuelhh_line("2026-01-15T12:30:00Z", "CCGT", 8100),
    ]
    rows = load_fuelhh(write(tmp_path, "fh.json", lines))
    assert rows == [
        ActualRow(start_time=datetime(2026, 1, 15, 12, tzinfo=UTC), generation_mw=9742),
        ActualRow(start_time=datetime(2026, 1, 15, 12, 30, tzinfo=UTC), generation_mw=9839),
    ]


def test_fuelhh_times_carry_utc(tmp_path):
    rows = load_fuelhh(write(tmp_path, "fh.json", [fuelhh_line("2026-01-15T12:30:00Z", "WIND", 1)]))
    assert rows[0].start_time.utcoffset() == timedelta(0)


# --- where the files are ---------------------------------------------------------------------


def test_paths_point_at_the_repo_data_folder():
    assert DATA_DIR == REPO / "data"
    assert WINDFOR_PATH == REPO / "data" / "windfor_2026-01.json"
    assert FUELHH_PATH == REPO / "data" / "fuelhh_2026-01.json"


# --- the real files ----------------------------------------------------------------------------


def test_real_windfor_file():
    rows = load_windfor(WINDFOR_PATH)
    assert len(rows) == 17_885
    assert all(r.publish_time.utcoffset() == timedelta(0) for r in rows)
    assert min(r.publish_time for r in rows) == datetime(2026, 1, 1, 2, 30, tzinfo=UTC)
    assert max(r.publish_time for r in rows) == datetime(2026, 1, 31, 11, 30, tzinfo=UTC)


def test_real_fuelhh_file():
    rows = load_fuelhh(FUELHH_PATH)
    assert len(rows) == 1_488
    assert all(r.start_time.utcoffset() == timedelta(0) for r in rows)


def test_loaded_rows_work_with_the_pick_rule():
    # The 1B warning: zone-less times would make every hour blank. Loaded rows must not.
    from windapp.pick import pick_day

    picked = pick_day(load_windfor(WINDFOR_PATH), date(2026, 1, 15), "09:20")
    assert picked[12].forecast_mw == 11_049
    assert all(p.forecast_mw is not None for p in picked)


def test_loaded_rows_work_with_hourly_actuals():
    from windapp.actuals import hourly_actuals

    hours = hourly_actuals(load_fuelhh(FUELHH_PATH))
    assert hours[datetime(2026, 1, 15, 12, tzinfo=UTC)].actual_mw == 9_790.5
