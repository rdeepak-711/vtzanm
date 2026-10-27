"""Download the January 2026 Elexon wind datasets."""

import json
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from windapp.load import FUELHH_PATH, WINDFOR_PATH


BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"


def elexon_urls(
    publish_from: datetime,
    publish_to: datetime,
    settlement_from: date,
    settlement_to: date,
) -> tuple[str, str]:
    """Build WINDFOR and WIND-only FUELHH stream URLs."""
    windfor = (
        f"{BASE_URL}/WINDFOR/stream"
        f"?publishDateTimeFrom={publish_from.strftime('%Y-%m-%dT%H:%MZ')}"
        f"&publishDateTimeTo={publish_to.strftime('%Y-%m-%dT%H:%MZ')}"
    )
    fuelhh = (
        f"{BASE_URL}/FUELHH/stream"
        f"?settlementDateFrom={settlement_from.isoformat()}"
        f"&settlementDateTo={settlement_to.isoformat()}&fuelType=WIND"
    )
    return windfor, fuelhh


def _download_json_list(url: str) -> bytes:
    """Download a JSON list and return its original response bytes."""
    with urlopen(url, timeout=30) as response:
        body = response.read()
    rows = json.loads(body)
    if not isinstance(rows, list):
        raise ValueError("Elexon response must be a JSON list")
    return body


def main() -> None:
    """Refresh the January 2026 fixture files from Elexon."""
    publish_from = datetime(2026, 1, 1, 0, 0)
    publish_to = datetime(2026, 1, 31, 12, 0)
    settlement_from = date(2026, 1, 2)
    settlement_to = date(2026, 2, 1)
    windfor_url, fuelhh_url = elexon_urls(
        publish_from, publish_to, settlement_from, settlement_to
    )

    for name, url, path in (
        ("WINDFOR", windfor_url, WINDFOR_PATH),
        ("FUELHH", fuelhh_url, FUELHH_PATH),
    ):
        body = _download_json_list(url)
        row_count = len(json.loads(body))
        path.write_bytes(body)
        print(f"{name}: {row_count} rows")


if __name__ == "__main__":
    main()
