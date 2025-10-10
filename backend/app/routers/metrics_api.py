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

    def pick(bm: Optional[BodyMetrics], at: Optional[Athlete], bm_attr: str, a_attr: Optional[str] = None):
        lv = getattr(bm, bm_attr) if (bm is not None and hasattr(bm, bm_attr)) else None
        av = getattr(at, a_attr) if (at is not None and a_attr) else None
        return lv if lv is not None else av

    return {
        "athlete_id": athlete_id,
        "date": (latest.date.isoformat() if latest else None),
        "metrics": {
            "weight_kg":       pick(latest, a, "weight_kg", "weight_kg"),
            "bodyfat_pct":     pick(latest, a, "bodyfat_pct", None),
            "vo2max_mlkgmin":  pick(latest, a, "vo2max_mlkgmin", "vo2max"),
            "resting_hr_bpm":  pick(latest, a, "resting_hr_bpm", "rhr"),
            "ftp_w":           pick(latest, a, "ftp_w", "ftp_w"),
        },
    }
