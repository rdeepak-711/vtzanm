"""Step 4: the FastAPI layer. Spec 'API' section, decision D7.

The API only translates: query string -> service call -> JSON, and service
errors -> 400 with a helpful message. All numbers come from the service.
"""

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from windapp.main import app

REPO = Path(__file__).resolve().parent.parent
client = TestClient(app)


# --- health ----------------------------------------------------------------------------------


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "delivery_days": {"from": "2026-01-02", "to": "2026-02-01"},
        "cutoffs": ["09:20", "09:50"],
    }


# --- day -------------------------------------------------------------------------------------


def test_day_15_jan():
    r = client.get("/api/day", params={"date": "2026-01-15", "cutoff": "09:20"})
    assert r.status_code == 200
    body = r.json()
    assert list(body) == ["date", "cutoff", "decision_time", "runs_used", "hours", "summary"]
    assert body["decision_time"] == "2026-01-14T09:20:00Z"
    assert body["runs_used"] == ["2026-01-14T07:30:00Z"]
    assert len(body["hours"]) == 24
    assert body["hours"][12]["forecast_mw"] == 11_049
    assert body["hours"][12]["error_mw"] == pytest.approx(1258.5, abs=0.1)
    assert body["summary"]["mae_mw"] == pytest.approx(1041.8, abs=0.1)


def test_day_cutoff_defaults_to_0920():
    body = client.get("/api/day", params={"date": "2026-01-15"}).json()
    assert body["cutoff"] == "09:20"


def test_day_0950_uses_the_0930_run():
    body = client.get("/api/day", params={"date": "2026-01-15", "cutoff": "09:50"}).json()
    assert body["runs_used"] == ["2026-01-14T09:30:00Z"]


# --- bad requests are 400, with a message that says what is allowed ----------------------------


def test_day_outside_the_window_is_400():
    r = client.get("/api/day", params={"date": "2026-01-01"})
    assert r.status_code == 400
    assert "2026-01-02" in r.json()["detail"]
    assert "2026-02-01" in r.json()["detail"]


def test_day_missing_date_is_400():
    r = client.get("/api/day")
    assert r.status_code == 400
    assert "date" in r.json()["detail"].lower()


@pytest.mark.parametrize("bad", ["2026-13-45", "15-01-2026", "yesterday", ""])
def test_day_unparseable_date_is_400(bad):
    r = client.get("/api/day", params={"date": bad})
    assert r.status_code == 400
    assert "2026-01-02" in r.json()["detail"]


def test_day_unknown_cutoff_is_400():
    r = client.get("/api/day", params={"date": "2026-01-15", "cutoff": "10:00"})
    assert r.status_code == 400
    assert "09:20" in r.json()["detail"] and "09:50" in r.json()["detail"]


def test_month_unknown_cutoff_is_400():
    r = client.get("/api/month", params={"cutoff": "10:00"})
    assert r.status_code == 400
    assert "09:20" in r.json()["detail"] and "09:50" in r.json()["detail"]


# --- month -------------------------------------------------------------------------------------


def test_month_0920():
    r = client.get("/api/month")
    assert r.status_code == 200
    body = r.json()
    assert list(body) == ["cutoff", "from", "to", "summary", "hours_off_by_1000",
                          "partial_hours", "by_hour_of_day", "by_day"]
    assert body["cutoff"] == "09:20"
    assert body["summary"]["n"] == 744
    assert body["summary"]["mae_mw"] == pytest.approx(2038.9, abs=0.1)
    assert body["summary"]["bias_mw"] == pytest.approx(1747.9, abs=0.1)
    assert body["summary"]["p90_mw"] == pytest.approx(4098.5, abs=0.1)
    assert body["hours_off_by_1000"] == 552
    assert len(body["by_hour_of_day"]) == 24
    assert len(body["by_day"]) == 31


def test_month_0950():
    body = client.get("/api/month", params={"cutoff": "09:50"}).json()
    assert body["cutoff"] == "09:50"
    assert body["summary"]["mae_mw"] == pytest.approx(2013.0, abs=0.1)


# --- the API must not change the service's cached answers ----------------------------------------


def test_repeated_calls_return_the_same_body():
    first = client.get("/api/day", params={"date": "2026-01-15"}).json()
    client.get("/api/month")
    second = client.get("/api/day", params={"date": "2026-01-15"}).json()
    assert first == second


# --- unknown paths ---------------------------------------------------------------------------------


def test_unknown_api_path_is_404():
    assert client.get("/api/nope").status_code == 404


# --- Vercel entry point ------------------------------------------------------------------------------


def test_vercel_entry_exposes_the_same_app():
    spec = importlib.util.spec_from_file_location("vercel_index", REPO / "api" / "index.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.app is app
