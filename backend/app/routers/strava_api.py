import os, time
from datetime import date
from typing import Optional, Dict, Any

import requests
from fastapi import APIRouter, Query, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import select

from db import SessionLocal
from models import Activity

router = APIRouter(prefix="/strava", tags=["strava"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_api_key(x_api_key: Optional[str] = Header(None)):
    api_key = os.getenv("API_KEY") or ""
    if not api_key or x_api_key != api_key:
        raise HTTPException(status_code=401, detail="unauthorized")
    return True

def _strava_refresh_token() -> str:
    """Return a short-lived access token, raising HTTPException with details on failure."""
    direct = os.getenv("STRAVA_ACCESS_TOKEN")
    if direct:
        return direct
    cid  = os.getenv("STRAVA_CLIENT_ID")
    csec = os.getenv("STRAVA_CLIENT_SECRET")
    rtok = os.getenv("STRAVA_REFRESH_TOKEN")
    if not all([cid, csec, rtok]):
        raise HTTPException(status_code=500, detail="strava_credentials_missing")
    try:
        resp = requests.post(
            "https://www.strava.com/oauth/token",
            data={"client_id": cid, "client_secret": csec, "grant_type": "refresh_token", "refresh_token": rtok},
            timeout=20,
        )
        txt = resp.text[:300]
        if resp.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"strava_token_error {resp.status_code}: {txt}")
        return resp.json()["access_token"]
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"strava_token_exception: {e}")

def _sport_map(t: str) -> str:
    return {
        "Ride":"bike","VirtualRide":"bike","EBikeRide":"bike","GravelRide":"bike",
        "Run":"run","Swim":"swim","Walk":"walk","Hike":"hike",
    }.get((t or "").strip(), "other")

def _estimate_tss(sport: str, duration_min: int) -> int:
    mult = 0.75 if sport == "bike" else 0.90 if sport == "run" else 0.60
    return int(round(duration_min * mult))

@router.get("/ping", dependencies=[Depends(require_api_key)])
def strava_ping() -> Dict[str, Any]:
    """Checks we can refresh a token. Does not call athlete endpoints."""
    token = _strava_refresh_token()
    return {"ok": True, "token_len": len(token)}

@router.post("/import", dependencies=[Depends(require_api_key)])
def strava_import(
    athlete_id: int = Query(..., ge=1),
    after_days: int = Query(30, ge=1, le=3650),
    db: Session = Depends(get_db),
):
    token = _strava_refresh_token()
    after = int(time.time()) - after_days * 86400
    headers = {"Authorization": f"Bearer {token}"}
    page, per_page = 1, 100
    imported = 0
    skipped = 0

    while True:
        try:
            r = requests.get(
                "https://www.strava.com/api/v3/athlete/activities",
                params={"after": after, "page": page, "per_page": per_page},
                headers=headers,
                timeout=30,
            )
            txt = r.text[:300]
            if r.status_code == 429:
                raise HTTPException(status_code=429, detail="strava_rate_limited")
            if r.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"strava_list_error {r.status_code}: {txt}")
            items = r.json() or []
        except requests.RequestException as e:
            raise HTTPException(status_code=502, detail=f"strava_list_exception: {e}")

        if not items:
            break

        for a in items:
            sport = _sport_map(a.get("type"))
            start = a.get("start_date_local") or a.get("start_date")
            if not start:
                skipped += 1; continue
            try:
                d = date.fromisoformat(start.split("T")[0])
            except Exception:
                skipped += 1; continue

            duration_min = int(round((a.get("moving_time") or 0) / 60))
            if duration_min <= 0:
                skipped += 1; continue

            tss = _estimate_tss(sport, duration_min)

            # de-dupe: same athlete + date + sport + duration
            existing = db.execute(
                select(Activity).where(
                    Activity.athlete_id == athlete_id,
                    Activity.date == d,
                    Activity.sport == sport,
                    Activity.duration_min == duration_min,
                )
            ).scalars().first()
            if existing:
                skipped += 1; continue

            db.add(Activity(
                athlete_id=athlete_id,
                date=d,
                sport=sport,
                duration_min=duration_min,
                tss=tss,
            ))
            imported += 1

        db.commit()
        page += 1

    return {"ok": True, "imported": imported, "skipped": skipped, "after_days": after_days}
