from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional

from db import SessionLocal
from models import BodyMetrics, Athlete

router = APIRouter(prefix="/metrics", tags=["metrics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/latest", include_in_schema=True)
def metrics_latest(athlete_id: int = Query(..., ge=1), db: Session = Depends(get_db)):
    latest: Optional[BodyMetrics] = db.execute(
        select(BodyMetrics)
        .where(BodyMetrics.athlete_id == athlete_id)
        .order_by(BodyMetrics.date.desc())
        .limit(1)
    ).scalars().first()

    a: Optional[Athlete] = db.get(Athlete, athlete_id)
    if latest is None and a is None:
        raise HTTPException(status_code=404, detail="athlete_not_found")

    return {
        "athlete_id": athlete_id,
        "date": (latest.date.isoformat() if latest else None),
        "metrics": {
            "weight_kg": (latest.weight_kg if latest else (a.weight_kg if a else None)),
            "bodyfat_pct": (latest.bodyfat_pct if latest else None),
            "vo2max_mlkgmin": (latest.vo2max_mlkgmin if latest else (a.vo2max if a else None)),
            "resting_hr_bpm": (latest.resting_hr_bpm if latest else (a.rhr if a else None)),
            "ftp_w": (latest.ftp_w if latest else (a.ftp_w if a else None)),
        },
    }
