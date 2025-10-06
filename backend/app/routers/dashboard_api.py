from fastapi import APIRouter, Query, HTTPException, Depends, Header
from datetime import date
import httpx
from app.config import API_BASE_URL, API_KEY, DEFAULT_LAT, DEFAULT_LON

router = APIRouter(prefix="/dashboard", tags=["dashboard"])  # URL stays /dashboard/...

def require_api_key(x_api_key: str = Header(default="")):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

@router.get("/today")
async def dashboard_today(
    athlete_id: int = Query(..., ge=1),
    lat: float | None = Query(None),
    lon: float | None = Query(None),
    indoor: bool = Query(False),
    _auth: bool = Depends(require_api_key),
):
    headers = {"x-api-key": API_KEY} if API_KEY else {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        # metrics
        m = await client.get(f"{API_BASE_URL}/metrics/latest", params={"athlete_id": athlete_id}, headers=headers)
        m.raise_for_status()
        metrics = m.json() or {}
        met = metrics.get("metrics", {}) if isinstance(metrics, dict) else {}

        # training plan (pick today's session from microcycle)
        tp = await client.get(
            f"{API_BASE_URL}/training/plan",
            params={"athlete_id": athlete_id, "indoor": str(indoor).lower()},
            headers=headers,
        )
        tp.raise_for_status()
        plan = tp.json() or {}
        today_str = str(date.today())
        session = None
        for s in (plan.get("microcycle") or []):
            if s.get("date") == today_str:
                session = s
                break
        # fallback: first session if no date match
        if session is None and (plan.get("microcycle") or []):
            session = plan["microcycle"][0]

        # nutrition
        n = await client.get(f"{API_BASE_URL}/nutrition/today", params={"athlete_id": athlete_id}, headers=headers)
        n.raise_for_status()
        nutrition = n.json()

        # weather (real)
        use_lat = lat if lat is not None else (met.get("home_lat") or DEFAULT_LAT)
        use_lon = lon if lon is not None else (met.get("home_lon") or DEFAULT_LON)
        w = await client.get(
        f"{API_BASE_URL}/weather/today",
        params={"lat": use_lat, "lon": use_lon},
        headers=headers,
        )
        w.raise_for_status()
        weather = w.json()

      

    notices = []
    ftp = met.get("ftp_w") or met.get("ftp_watts")
    if ftp in (None, 0, "null"):
        notices.append("FTP missing: schedule test or enable auto-derivation.")

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
        "nutrition": nutrition.get("targets") if isinstance(nutrition, dict) else nutrition,
        "weather": weather,
        "notices": notices,
        "source": {
            "metrics": f"{API_BASE_URL}/metrics/latest",
            "plan": f"{API_BASE_URL}/training/plan",
            "nutrition": f"{API_BASE_URL}/nutrition/today",
        },
    }