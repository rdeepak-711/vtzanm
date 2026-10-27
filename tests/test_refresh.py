"""Step 2: the Elexon download script. Spec 'scripts/refresh_data.py', decision D6.

Only the URL builder is tested. Nothing here touches the network: a test that
downloads would fail offline (Codex's sandbox) or whenever Elexon is slow.
"""

from datetime import date, datetime, timezone
from urllib.parse import parse_qs, urlparse

import refresh_data
from refresh_data import elexon_urls

UTC = timezone.utc

JANUARY = dict(
    publish_from=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
    publish_to=datetime(2026, 1, 31, 12, 0, tzinfo=UTC),
    settlement_from=date(2026, 1, 2),
    settlement_to=date(2026, 2, 1),
)


def test_returns_windfor_then_fuelhh():
    windfor, fuelhh = elexon_urls(**JANUARY)
    assert "/datasets/WINDFOR/" in windfor
    assert "/datasets/FUELHH/" in fuelhh


def test_windfor_url_exactly():
    windfor, _ = elexon_urls(**JANUARY)
    assert windfor == (
        "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream"
        "?publishDateTimeFrom=2026-01-01T00:00Z&publishDateTimeTo=2026-01-31T12:00Z"
    )


def test_fuelhh_url_exactly():
    _, fuelhh = elexon_urls(**JANUARY)
    assert fuelhh == (
        "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream"
        "?settlementDateFrom=2026-01-02&settlementDateTo=2026-02-01&fuelType=WIND"
    )


def test_windfor_is_filtered_by_when_forecasts_were_made():
    windfor, _ = elexon_urls(**JANUARY)
    params = parse_qs(urlparse(windfor).query)
    assert set(params) == {"publishDateTimeFrom", "publishDateTimeTo"}


def test_fuelhh_is_filtered_by_delivery_day_and_wind_only():
    _, fuelhh = elexon_urls(**JANUARY)
    params = parse_qs(urlparse(fuelhh).query)
    assert params["settlementDateFrom"] == ["2026-01-02"]
    assert params["settlementDateTo"] == ["2026-02-01"]
    assert params["fuelType"] == ["WIND"]


def test_other_dates_flow_through():
    windfor, fuelhh = elexon_urls(
        publish_from=datetime(2026, 3, 5, 6, 7, tzinfo=UTC),
        publish_to=datetime(2026, 3, 9, 23, 30, tzinfo=UTC),
        settlement_from=date(2026, 3, 6),
        settlement_to=date(2026, 3, 10),
    )
    assert "publishDateTimeFrom=2026-03-05T06:07Z" in windfor
    assert "publishDateTimeTo=2026-03-09T23:30Z" in windfor
    assert "settlementDateFrom=2026-03-06" in fuelhh
    assert "settlementDateTo=2026-03-10" in fuelhh


def test_main_exists_but_importing_the_script_downloads_nothing():
    # Importing must be safe offline: the download only runs via main().
    assert callable(refresh_data.main)
