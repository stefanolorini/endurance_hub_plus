from fastapi import APIRouter, Query, HTTPException, Header
from typing import Optional, Tuple, Any, Dict
from datetime import date
import httpx
from app.config import API_BASE_URL, API_KEY, DEFAULT_LAT, DEFAULT_LON

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

async def fetch_json(client: httpx.AsyncClient, url: str, params: Dict[str, Any], headers: Dict[str, str], label: str) -> Tuple[Optional[dict], Optional[str]]:
    try:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        try:
            return r.json() or {}, None
        except ValueError:
            return None, f"{label}_invalid_json"
    except httpx.HTTPError as e:
        return None, f"{label}_http_error:{e}"

@router.get("/today")
async def dashboard_today(
    athlete_id: int = Query(..., ge=1),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    indoor: bool = Query(False),
    x_api_key: Optional[str] = Header(None),  # reads 'x-api-key'
):
    # Only enforce if client sent a non-empty header
    if API_KEY and x_api_key and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    headers = {"x-api-key": API_KEY} if API_KEY else {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        # metrics
        metrics, err_metrics = await fetch_json(
            client, f"{API_BASE_URL}/metrics/latest",
            {"athlete_id": athlete_id}, headers, "metrics"
        )
        met = (metrics.get("metrics") if isinstance(metrics, dict) else {}) if metrics else {}
        # training plan
        plan, err_plan = await fetch_json(
            client, f"{API_BASE_URL}/training/plan",
            {"athlete_id": athlete_id, "indoor": str(indoor).lower()}, headers, "plan"
        )
        today_str = str(date.today())
        session = None
        if isinstance(plan, dict):
            for s in (plan.get("microcycle") or []):
                if s.get("date") == today_str:
                    session = s
                    break
            if session is None and (plan.get("microcycle") or []):
                session = plan["microcycle"][0]

        # nutrition
        nutrition, err_nut = await fetch_json(
            client, f"{API_BASE_URL}/nutrition/today",
            {"athlete_id": athlete_id}, headers, "nutrition"
        )

        # weather (safe fallbacks)
        fallback_lat = DEFAULT_LAT if DEFAULT_LAT is not None else 48.21
        fallback_lon = DEFAULT_LON if DEFAULT_LON is not None else 16.37
        use_lat = lat if (lat is not None) else (met.get("home_lat") or fallback_lat)
        use_lon = lon if (lon is not None) else (met.get("home_lon") or fallback_lon)
        weather, err_weather = await fetch_json(
            client, f"{API_BASE_URL}/weather/today",
            {"lat": use_lat, "lon": use_lon}, headers, "weather"
        )

    notices = []
    ftp = met.get("ftp_w") or met.get("ftp_watts")
    if ftp in (None, 0, "null"):
        notices.append("FTP missing: schedule test or enable auto-derivation.")

    errors = [e for e in [err_metrics, err_plan, err_nut, err_weather] if e]

    return {
        "date": str(date.today()),
        "readiness": {
            "hr_rest": met.get("resting_hr_bpm") or met.get("hr_rest"),
            "hrv_ms": met.get("hrv_ms"),
            "sleep_h": met.get("sleep_hours"),
            "status": met.get("readiness_status", "unknown"),
            "notes": met.get("readiness_notes"),
        },
        "session": session,
        "nutrition": (nutrition.get("targets") if isinstance(nutrition, dict) else nutrition) if nutrition else None,
        "weather": weather if weather else {"error": "weather_unavailable"},
        "notices": notices,
        "errors": errors or None,
        "source": {
            "metrics": f"{API_BASE_URL}/metrics/latest",
            "plan": f"{API_BASE_URL}/training/plan",
            "nutrition": f"{API_BASE_URL}/nutrition/today",
        },
    }
