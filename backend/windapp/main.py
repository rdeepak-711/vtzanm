"""FastAPI endpoints for the day-ahead wind forecast."""

from datetime import date as date_type
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from windapp import service

app = FastAPI(title="Day-ahead wind forecast")

DATE_DETAIL = "Date must be YYYY-MM-DD between 2026-01-02 and 2026-02-01"


@app.get("/api/health")
def health() -> dict:
    """Return basic API and delivery window information."""
    return {
        "status": "ok",
        "delivery_days": {"from": "2026-01-02", "to": "2026-02-01"},
        "cutoffs": ["09:20", "09:50"],
    }


@app.get("/api/day")
def day(date: str | None = None, cutoff: str = "09:20") -> dict:
    """Return the forecast accuracy view for one delivery day."""
    if date is None:
        raise HTTPException(status_code=400, detail=DATE_DETAIL)
    try:
        delivery_day = date_type.fromisoformat(date)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=DATE_DETAIL) from error
    try:
        return service.day_view(delivery_day, cutoff)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/month")
def month(cutoff: str = "09:20") -> dict:
    """Return aggregate accuracy for the delivery month."""
    try:
        return service.month_view(cutoff)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def add_frontend(app: FastAPI, dist: Path) -> None:
    """Serve frontend files and fall back to its entry point when built."""
    if not dist.exists():
        return

    resolved_dist = dist.resolve()

    @app.get("/{path:path}")
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)

        file_path = (dist / path).resolve()
        try:
            file_path.relative_to(resolved_dist)
        except ValueError:
            file_path = resolved_dist / "index.html"

        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(resolved_dist / "index.html")


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
add_frontend(app, frontend_dist)
