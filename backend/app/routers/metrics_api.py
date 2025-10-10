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

def last_non_null(db: Session, athlete_id: int, col_name: str):
    col = getattr(BodyMetrics, col_name)
    row = db.execute(
        select(BodyMetrics.date, col)
        .where(BodyMetrics.athlete_id == athlete_id, col.is_not(None))
        .order_by(BodyMetrics.date.desc())
        .limit(1)
    ).first()
    return (row[0], row[1]) if row else (None, None)

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

    # For each metric: prefer latest row value; else most recent non-null; else Athlete snapshot
    _, w_val   = last_non_null(db, athlete_id, "weight_kg")
    _, bf_val  = last_non_null(db, athlete_id, "bodyfat_pct")
    _, vo2_val = last_non_null(db, athlete_id, "vo2max_mlkgmin")
    _, rhr_val = last_non_null(db, athlete_id, "resting_hr_bpm")
    _, ftp_val = last_non_null(db, athlete_id, "ftp_w")

    weight = (latest.weight_kg        if latest and latest.weight_kg        is not None else w_val)   or (a.weight_kg if a else None)
    bodyfat= (latest.bodyfat_pct      if latest and latest.bodyfat_pct      is not None else bf_val)
    vo2    = (latest.vo2max_mlkgmin   if latest and latest.vo2max_mlkgmin   is not None else vo2_val) or ((a.vo2max if a else None))
    rhr    = (latest.resting_hr_bpm   if latest and latest.resting_hr_bpm   is not None else rhr_val) or ((a.rhr    if a else None))
    ftp    = (latest.ftp_w            if latest and latest.ftp_w            is not None else ftp_val) or ((a.ftp_w  if a else None))

    return {
        "athlete_id": athlete_id,
        "date": (latest.date.isoformat() if latest else None),
        "metrics": {
            "weight_kg": weight,
            "bodyfat_pct": bodyfat,
            "vo2max_mlkgmin": vo2,
            "resting_hr_bpm": rhr,
            "ftp_w": ftp,
        },
    }
