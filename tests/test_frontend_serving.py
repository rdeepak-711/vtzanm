"""Serving the built React app from FastAPI (one-process run: Docker, preview).

React decides the screen from the address, so every non-API page must get
index.html, while real files (JS, CSS) are served as themselves and unknown
/api paths stay 404.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from windapp.main import add_frontend


def built_app(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>APP</html>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    add_frontend(app, dist)
    return TestClient(app)


def test_root_serves_index(tmp_path):
    r = built_app(tmp_path).get("/")
    assert r.status_code == 200 and "APP" in r.text


def test_month_page_serves_index(tmp_path):
    r = built_app(tmp_path).get("/month", params={"cutoff": "09:50"})
    assert r.status_code == 200 and "APP" in r.text


def test_real_files_are_served_as_themselves(tmp_path):
    r = built_app(tmp_path).get("/assets/app.js")
    assert r.status_code == 200 and "console.log" in r.text


def test_api_routes_still_work(tmp_path):
    assert built_app(tmp_path).get("/api/ping").json() == {"ok": True}


def test_unknown_api_path_is_still_404(tmp_path):
    assert built_app(tmp_path).get("/api/nope").status_code == 404


def test_missing_dist_adds_nothing(tmp_path):
    app = FastAPI()
    add_frontend(app, tmp_path / "no-such-dist")
    assert TestClient(app).get("/").status_code == 404
