import os
import logging
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Body, Query, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text, select, func
from sqlalchemy.orm import Session

from db import engine, SessionLocal
from models import Base, Athlete, TrainingBlock

log = logging.getLogger("uvicorn.error")

# Optional models (ok if not present yet)
try:
    from models import Goal
except Exception:
    Goal = None  # type: ignore

try:
    from models import Activity
except Exception:
    Activity = None  # type: ignore

try:
    from models import BodyMetrics
except Exception:
    BodyMetrics = None  # type: ignore


app = FastAPI(title="Holistic Health & Training API", version="0.1")

# CORS (dev-open)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dev bootstrap (optional): create tables for known models
if os.getenv("DEV_BOOTSTRAP", "0") == "1":
    Base.metadata.create_all(bind=engine)


# ---------------- DB session ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- Health ----------------
@app.get("/health")
def health() -> Dict[str, str]:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}


# ---------------- Athlete basic ----------------
@app.get("/athlete/{athlete_id}")
def get_athlete(athlete_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    a = db.get(Athlete, athlete_id)
    if not a:
        raise HTTPException(status_code=404, detail="athlete_not_found")
    return {
        "id": a.id,
        "name": a.name,
        "sex": a.sex,
        "age": a.age,
        "height_cm": a.height_cm,
        "weight_kg": a.weight_kg,
        "rhr": a.rhr,
        "vo2max": a.vo2max,
        "ftp_w": a.ftp_w,
    }


@app.patch("/athlete/{athlete_id}")
def update_athlete(athlete_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    a = db.get(Athlete, athlete_id)
    if not a:
        raise HTTPException(status_code=404, detail="athlete_not_found")
    for k in ["ftp_w", "vo2max", "rhr", "weight_kg", "height_cm", "age"]:
        if k in payload and payload[k] is not None:
            setattr(a, k, payload[k])
    db.commit(); db.refresh(a)
    return {"ok": True, "athlete_id": a.id, "ftp_w": a.ftp_w, "vo2max": a.vo2max}


# ================= Helpers: planning / sessions =================
POWER_ZONE_TARGET_IF = {
    "recovery": 0.55,
    "endurance": 0.65,
    "tempo": 0.80,
    "sweetspot": 0.88,
    "threshold": 0.95,
    "vo2": 1.05,
}

def _to_float(v):
    try:
        return float(v)
    except Exception:
        return None

def estimate_tss(duration_min: int, intensity_factor: float) -> int:
    hours = duration_min / 60.0
    return int(round(hours * (intensity_factor ** 2) * 100.0))

def is_recovery_week(start_date, block_len_weeks: int, recovery_weeks: int, ref_date):
    if not start_date or not block_len_weeks:
        return False
    cycle = block_len_weeks + (recovery_weeks or 0)
    if cycle <= 0:
        return False
    week_index = (ref_date - start_date).days // 7
    return (week_index % cycle) >= block_len_weeks

def session_endurance(day: date, duration_min: int, ftp_w: float):
    IF = POWER_ZONE_TARGET_IF["endurance"]
    return {
        "date": day.isoformat(),
        "sport": "bike",
        "title": "Endurance Z2",
        "details": "Steady Z2; cadence 85–95rpm; 3×5min high-cadence 100–110rpm",
        "duration_min": duration_min,
        "intensity_factor": IF,
        "target_power_w": [0.56 * ftp_w, 0.75 * ftp_w] if ftp_w else None,
        "indoor_ok": True,
        "tss": estimate_tss(duration_min, IF),
    }

def session_sweetspot(day: date, ftp_w: float, main_intervals=(2, 15)):
    IF = POWER_ZONE_TARGET_IF["sweetspot"]
    reps, mins = main_intervals
    duration_min = 20 + reps * mins + (reps - 1) * 5
    return {
        "date": day.isoformat(),
        "sport": "bike",
        "title": f"Sweet Spot {reps}×{mins}min @ 88–92% FTP",
        "details": "WU 10–15min; SS work; 5min rec; CD 10min",
        "duration_min": duration_min,
        "intensity_factor": IF,
        "target_power_w": [0.88 * ftp_w, 0.92 * ftp_w] if ftp_w else None,
        "indoor_ok": True,
        "tss": estimate_tss(duration_min, IF),
    }

def session_threshold(day: date, ftp_w: float, main_intervals=(3, 10)):
    IF = POWER_ZONE_TARGET_IF["threshold"]
    reps, mins = main_intervals
    duration_min = 20 + reps * mins + (reps - 1) * 5
    return {
        "date": day.isoformat(),
        "sport": "bike",
        "title": f"Threshold {reps}×{mins}min @ 95–100% FTP",
        "details": "WU 15–20min; 3–4×8–10min @ 95–100%; 5min rec; CD 10–15min",
        "duration_min": duration_min,
        "intensity_factor": IF,
        "target_power_w": [0.95 * ftp_w, 1.00 * ftp_w] if ftp_w else None,
        "indoor_ok": True,
        "tss": estimate_tss(duration_min, IF),
    }

def session_long_endurance(day: date, hours: float, ftp_w: float):
    duration_min = int(hours * 60)
    IF = 0.68
    return {
        "date": day.isoformat(),
        "sport": "bike",
        "title": f"Long Endurance {hours:.1f}h",
        "details": "Mostly Z2; add 2×20min low-Z3 climbs if feeling good",
        "duration_min": duration_min,
        "intensity_factor": IF,
        "target_power_w": [0.60 * ftp_w, 0.75 * ftp_w] if ftp_w else None,
        "indoor_ok": False,
        "tss": estimate_tss(duration_min, IF),
    }

def session_indoor_endurance(day: date, ftp_w: float):
    duration_min = 120
    IF = 0.72
    return {
        "date": day.isoformat(),
        "sport": "bike",
        "title": "Indoor Endurance Builder 2.0h",
        "details": "WU 15min Z2 → 3×12min @ 88–92% FTP (5min easy) → Z2 steady; CD 10min",
        "duration_min": duration_min,
        "intensity_factor": IF,
        "target_power_w": [0.60 * ftp_w, 0.92 * ftp_w] if ftp_w else None,
        "indoor_ok": True,
        "tss": estimate_tss(duration_min, IF),
    }

def session_mobility(day: date, minutes=45):
    return {
        "date": day.isoformat(),
        "sport": "strength",
        "title": "Strength & Mobility",
        "details": "Core 15min + mobility 20min + glute activation 10min",
        "duration_min": minutes,
        "intensity_factor": 0.0,
        "target_power_w": None,
        "indoor_ok": True,
        "tss": 0,
    }

def session_rest(day: date, minutes=30):
    return {
        "date": day.isoformat(),
        "sport": "rest",
        "title": "Rest / Easy Walk",
        "details": "Optional 20–30min easy walk or spin <Z1",
        "duration_min": minutes,
        "intensity_factor": 0.0,
        "target_power_w": None,
        "indoor_ok": True,
        "tss": 0,
    }

def recent_7d_tss(db: Session, athlete_id: int, ref_day: date) -> int:
    if Activity is None:
        return 0
    start = ref_day - timedelta(days=6)
    total = db.execute(
        select(func.coalesce(func.sum(Activity.tss), 0))
        .where(Activity.athlete_id == athlete_id)
        .where(Activity.date >= start)
        .where(Activity.date <= ref_day)
    ).scalar()
    return int(total or 0)

def generate_week_plan(
    athlete: Athlete,
    blk: Optional[TrainingBlock],
    start_date: date,
    *,
    fatigue_7d: int = 0,
    indoor: bool = False,
):
    ftp = float(athlete.ftp_w or 0)
    recovery = is_recovery_week(
        blk.start_date if blk else None,
        blk.block_length_weeks if blk else 3,
        blk.recovery_weeks if blk else 1,
        start_date,
    )
    plan: List[Dict[str, Any]] = []
    for i in range(7):
        day = start_date + timedelta(days=i)
        wd = day.weekday()  # Mon=0 ... Sun=6
        if recovery:
            if wd in (0, 4):       plan.append(session_rest(day))
            elif wd in (1, 3):     plan.append(session_mobility(day, 35))
            elif wd in (2, 5):     plan.append(session_endurance(day, 50, ftp))
            else:                  plan.append(session_endurance(day, 60, ftp))
        else:
            if wd == 0:
                plan.append(session_rest(day))
            elif wd == 1:
                plan.append(session_endurance(day, 75, ftp))
            elif wd == 2:
                plan.append(session_sweetspot(day, ftp, (2, 15)))
            elif wd == 3:
                plan.append(session_endurance(day, 60, ftp))
            elif wd == 4:
                plan.append(session_mobility(day))
            elif wd == 5:
                plan.append(session_indoor_endurance(day, ftp) if indoor else session_long_endurance(day, 3.0, ftp))
            else:
                if fatigue_7d >= 500:
                    s = session_endurance(day, 90, ftp)
                    s["title"] = "Endurance Z2 (fatigue gate)"
                    s["adjusted_for_fatigue"] = True
                    plan.append(s)
                else:
                    plan.append(session_threshold(day, ftp, (3, 10)))
    return plan
# =============== /helpers ===============


# ---------------- Plan Preview (free-text goal) ----------------
class PlanRequest(BaseModel):
    goal_text: str
    weeks: Optional[int] = None
    start_date: Optional[date] = None

def _infer_plan_type(text_in: str) -> str:
    t = text_in.lower()
    if any(k in t for k in ["ftp", "cycling", "bike", "time trial", "sweet spot", "threshold"]):
        return "cycling_ftp"
    if any(k in t for k in ["fat loss", "cut", "lose fat", "weight loss"]):
        return "fat_loss"
    if "marathon" in t: return "run_marathon"
    if "half marathon" in t: return "run_half"
    if "10k" in t or "10 km" in t: return "run_10k"
    if "5k" in t or "5 km" in t: return "run_5k"
    if "tri" in t or "ironman" in t: return "triathlon"
    return "cycling_ftp"  # default

def _latest_metrics(db, athlete_id: int) -> Dict:
    if BodyMetrics is None:
        a = db.get(Athlete, athlete_id)
        return {
            "weight_kg": a.weight_kg if a else None,
            "bodyfat_pct": None, "vo2max_mlkgmin": None, "resting_hr_bpm": None,
            "ftp_w": a.ftp_w if a else None, "sex": a.sex if a else "male",
            "age": a.age if a else 35, "height_cm": a.height_cm if a else 176.0
        }

    def pick(field):
        col = getattr(BodyMetrics, field)
        row = db.execute(
            select(BodyMetrics.date, col)
            .where(BodyMetrics.athlete_id == athlete_id, col.is_not(None))
            .order_by(BodyMetrics.date.desc())
            .limit(1)
        ).first()
        return (row[0], row[1]) if row else (None, None)

    _, weight = pick("weight_kg")
    _, bodyfat = pick("bodyfat_pct")
    _, vo2 = pick("vo2max_mlkgmin")
    _, rhr = pick("resting_hr_bpm")
    _, ftp = pick("ftp_w")

    prof = db.execute(
        select(text("sex"), text("age"), text("height_cm"), text("weight_kg"))
        .select_from(text("athlete"))
        .where(text("id = :aid")), {"aid": athlete_id}
    ).first()
    sex = prof[0] if prof else "male"
    age = int(prof[1]) if prof and prof[1] is not None else 35
    height_cm = float(prof[2]) if prof and prof[2] is not None else 176.0
    fallback_weight = float(prof[3]) if prof and prof[3] is not None else None

    return {
        "weight_kg": weight or fallback_weight,
        "bodyfat_pct": bodyfat,
        "vo2max_mlkgmin": vo2,
        "resting_hr_bpm": rhr,
        "ftp_w": ftp,
        "sex": sex,
        "age": age,
        "height_cm": height_cm,
    }

def _nutrition_targets(sex:str, age:int, height_cm:float, weight_kg:float,
                       activity_factor:float, goal_type:str, rate_kg_wk:float,
                       protein_g_per_kg:float, fat_g_per_kg:float) -> Dict:
    if sex.lower() == "male":
        bmr = 10*weight_kg + 6.25*height_cm - 5*age + 5
    else:
        bmr = 10*weight_kg + 6.25*height_cm - 5*age - 161
    tdee = bmr * activity_factor
    delta = 0.0
    if goal_type == "fat_loss":
        delta = - (7700.0 * rate_kg_wk) / 7.0
    elif goal_type == "gain":
        delta = + (7700.0 * rate_kg_wk) / 7.0
    calories = max(1200.0, tdee + delta)
    protein_g = protein_g_per_kg * weight_kg
    fat_g = fat_g_per_kg * weight_kg
    carbs_g = max(0.0, (calories - (protein_g*4 + fat_g*9)) / 4.0)
    return {
        "calories": round(calories, 0),
        "protein_g": round(protein_g, 0),
        "fat_g": round(fat_g, 0),
        "carbs_g": round(carbs_g, 0),
        "bmr": round(bmr,1), "tdee": round(tdee,1)
    }

def _supplements_for(plan_type:str) -> List[Dict]:
    common = [
        {"name":"Creatine monohydrate","dose":"3–5 g/day","timing":"anytime","evidence":"strong"},
        {"name":"Caffeine","dose":"3 mg/kg pre-key session","timing":"~60 min pre","evidence":"strong"},
        {"name":"Omega-3 (EPA/DHA)","dose":"1–2 g/day","timing":"with meals","evidence":"moderate"},
        {"name":"Vitamin D3","dose":"1000–2000 IU/day","timing":"with fat","evidence":"contextual"}
    ]
    if plan_type == "cycling_ftp":
        common.append({"name":"Beta-alanine","dose":"3.2–6.4 g/day","timing":"split doses","evidence":"moderate"})
    return common

def _adaptation_rules(plan_type:str) -> List[Dict]:
    return [
        {"trigger":"7-day actual TSS > planned TSS by ≥20%","action":"Drop Thu intensity this week; keep Z2 only."},
        {"trigger":"Resting HR +8 bpm for 3 days OR poor sleep","action":"Replace Tue threshold with 45' Z2; resume next week."},
        {"trigger":"Weight loss >1%/wk for 2 wks","action":"+200 kcal on rest & training days; hold until <0.7%/wk."},
        {"trigger":"FTP test shows +3% or more","action":"Raise zone watt targets accordingly from next microcycle."},
    ]

def _cycling_week_template(week_idx: int, ftp: Optional[float]) -> Dict:
    is_recovery = (week_idx % 4 == 0)
    bump = 1.0 + 0.05 * ((week_idx - 1) % 4)
    if is_recovery:
        sessions = [
            {"day":"Mon","type":"Rest","duration_min":0,"intensity":"Rest","notes":"Off or mobility"},
            {"day":"Tue","type":"Endurance","duration_min":60,"intensity":"Z2","notes":"Keep easy"},
            {"day":"Wed","type":"Endurance","duration_min":45,"intensity":"Z1-2","notes":"Spin only"},
            {"day":"Thu","type":"Tempo","duration_min":50,"intensity":"Tempo","notes":"3x8' @ 80% FTP, 4' easy"},
            {"day":"Fri","type":"Rest","duration_min":0,"intensity":"Rest","notes":"Off"},
            {"day":"Sat","type":"Endurance","duration_min":90,"intensity":"Z2","notes":"Low cadence drills"},
            {"day":"Sun","type":"Endurance","duration_min":60,"intensity":"Z2","notes":"Keep it comfy"},
        ]
    else:
        sessions = [
            {"day":"Mon","type":"Rest","duration_min":0,"intensity":"Rest","notes":"Off or mobility"},
            {"day":"Tue","type":"Threshold","duration_min":75*bump,"intensity":"Threshold","notes":"3x10' @ 95–100% FTP, 5' easy"},
            {"day":"Wed","type":"Endurance","duration_min":60*bump,"intensity":"Z2","notes":"Nose-breathing Z2"},
            {"day":"Thu","type":"Sweet Spot","duration_min":80*bump,"intensity":"Sweet Spot","notes":"2x20' @ 88–92% FTP, 5' easy"},
            {"day":"Fri","type":"Optional Strength","duration_min":30,"intensity":"Gym","notes":"Hinge + squat + core"},
            {"day":"Sat","type":"Endurance Long","duration_min":150*bump,"intensity":"Z2","notes":"Café ride, steady"},
            {"day":"Sun","type":"Endurance","duration_min":90*bump,"intensity":"Z2","notes":"Spin out"},
        ]
    IF_map = {"Rest":0.0,"Z1-2":0.6,"Z2":0.65,"Tempo":0.80,"Sweet Spot":0.88,"Threshold":0.96,"VO2":1.05,"Gym":0.3}
    for s in sessions:
        IF = IF_map.get(s["intensity"], 0.65)
        s["tss"] = 0 if s["duration_min"]==0 else estimate_tss(int(s["duration_min"]), IF)
        if ftp and s["intensity"] in ("Sweet Spot","Threshold","Tempo","Z2"):
            if s["intensity"] == "Sweet Spot":
                s["target_watts"] = [round(0.88*ftp), round(0.92*ftp)]
            elif s["intensity"] == "Threshold":
                s["target_watts"] = [round(0.95*ftp), round(1.00*ftp)]
            elif s["intensity"] == "Tempo":
                s["target_watts"] = [round(0.76*ftp), round(0.88*ftp)]
            elif s["intensity"] == "Z2":
                s["target_watts"] = [round(0.60*ftp), round(0.70*ftp)]
    focus = "Recovery" if is_recovery else f"Build {((week_idx-1)%4)+1}"
    return {"focus": focus, "sessions": sessions}

def _generate_plan_for_you(db, athlete_id:int, goal_text:str, weeks:int, start:date) -> Dict:
    m = _latest_metrics(db, athlete_id)
    plan_type = _infer_plan_type(goal_text)
    weeks = weeks or 6
    ftp = m.get("ftp_w")
    sex, age, height_cm, weight_kg = m.get("sex"), m.get("age"), m.get("height_cm"), m.get("weight_kg")
    if weight_kg is None:
        weight_kg = 75.0

    blocks = []
    for w in range(1, weeks+1):
        week = _cycling_week_template(w, ftp)
        wd = start + timedelta(days=(w-1)*7)
        week["week"] = w
        week["start_date"] = wd.isoformat()
        blocks.append(week)

    train_targets = _nutrition_targets(sex, age, height_cm, weight_kg, 1.6, "maintenance", 0.0, 1.8, 0.8)
    rest_targets  = _nutrition_targets(sex, age, height_cm, weight_kg, 1.4, "maintenance", 0.0, 1.8, 0.8)

    return {
        "plan_type": plan_type,
        "summary": {
            "goal_text": goal_text,
            "weeks": weeks,
            "start_date": start.isoformat(),
            "athlete_snapshot": {k: m.get(k) for k in ["weight_kg","bodyfat_pct","vo2max_mlkgmin","resting_hr_bpm","ftp_w","sex","age","height_cm"]}
        },
        "blocks": blocks,
        "nutrition": {
            "training_day": train_targets,
            "rest_day": rest_targets,
            "distribution_hint": "Aim for ~4 meals/day; put most carbs around Tue/Thu/Sat sessions."
        },
        "supplements": _supplements_for(plan_type),
        "adaptation_rules": _adaptation_rules(plan_type),
        "notes": "Preview. We can add a save endpoint later to persist this plan."
    }

@app.post("/plan/preview")
def plan_preview(athlete_id:int, req: PlanRequest, db: Session = Depends(get_db)):
    start = req.start_date or date.today()
    return _generate_plan_for_you(db, athlete_id, req.goal_text, req.weeks or 6, start)


# ---------------- Training plan snapshot ----------------
@app.get("/training/plan")
def get_training_plan(
    athlete_id: int,
    indoor: bool = Query(False),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    a = db.get(Athlete, athlete_id)
    if not a:
        raise HTTPException(status_code=404, detail="athlete_not_found")

    blk = (
        db.execute(
            select(TrainingBlock)
            .where(TrainingBlock.athlete_id == athlete_id)
            .order_by(TrainingBlock.start_date.desc())
        ).scalars().first()
    )

    start = date.today()
    fatigue7 = recent_7d_tss(db, athlete_id, start)
    microcycle = generate_week_plan(a, blk, start, fatigue_7d=fatigue7, indoor=indoor)

    latest_goal = None
    if Goal is not None:
        latest_goal = (
            db.execute(
                select(Goal)
                .where(Goal.athlete_id == athlete_id, Goal.active == True)  # noqa: E712
                .order_by(Goal.created_at.desc())
            ).scalars().first()
        )

    return {
        "athlete_id": athlete_id,
        "block": {
            "start_date": (blk.start_date.isoformat() if blk else None),
            "weeks": (blk.block_length_weeks if blk else 3),
            "recovery_weeks": (blk.recovery_weeks if blk else 1),
            "is_recovery_week": is_recovery_week(
                blk.start_date if blk else None,
                (blk.block_length_weeks if blk else 3),
                (blk.recovery_weeks if blk else 1),
                start,
            ),
        },
        "context": {"fatigue_7d_tss": fatigue7, "indoor": indoor},
        "goal": None if not latest_goal else {
            "target_weight_kg": latest_goal.target_weight_kg,
            "target_bodyfat_pct": latest_goal.target_bodyfat_pct,
            "target_ftp_w": latest_goal.target_ftp_w,
            "timeframe_weeks": latest_goal.timeframe_weeks,
            "goal_prompt": latest_goal.goal_prompt,
        },
        "microcycle": microcycle,
        "generated_at": start.isoformat(),
    }


# ---------------- Activities ----------------
@app.get("/activities/recent")
def get_recent_activities(athlete_id: int) -> Dict[str, Any]:
    return {"athlete_id": athlete_id, "items": []}

@app.post("/activities")
def add_activity(payload: dict = Body(...), db: Session = Depends(get_db)):
    if Activity is None:
        raise HTTPException(status_code=501, detail="Activity model not available.")
    try:
        d = date.fromisoformat(payload["date"])
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_date_format (expected YYYY-MM-DD)")
    a = Activity(
        athlete_id=int(payload["athlete_id"]),
        date=d,
        sport=payload.get("sport", "bike"),
        duration_min=payload.get("duration_min"),
        tss=payload.get("tss"),
    )
    db.add(a); db.commit(); db.refresh(a)
    return {"ok": True, "id": a.id}


# ---------------- Nutrition (simple targets) ----------------
@app.get("/nutrition/today")
def get_nutrition_today(athlete_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    a = db.get(Athlete, athlete_id)
    if not a:
        raise HTTPException(status_code=404, detail="athlete_not_found")
    kcal_target = round(30 * a.weight_kg)
    return {
        "athlete_id": athlete_id,
        "date": date.today().isoformat(),
        "targets": {
            "kcal": kcal_target,
            "protein_g": round(1.6 * a.weight_kg),
            "carbs_g": None,
            "fat_g": None,
        },
        "meals": [],
    }


# ---------------- Goals (basic) ----------------
@app.post("/goals")
def upsert_goals(payload: dict = Body(...), db: Session = Depends(get_db)):
    if Goal is None:
        raise HTTPException(status_code=501, detail="Goal model not available yet. Add it in models.py and restart.")
    athlete_id = int(payload["athlete_id"])
    db.execute(
        text("UPDATE goals SET active=false WHERE athlete_id=:aid AND active=true"),
        {"aid": athlete_id},
    )
    g = Goal(
        athlete_id=athlete_id,
        target_weight_kg=payload.get("target_weight_kg"),
        target_bodyfat_pct=payload.get("target_bodyfat_pct"),
        target_ftp_w=payload.get("target_ftp_w"),
        goal_prompt=payload.get("goal_prompt"),
        parsed_constraints=payload.get("parsed_constraints"),
        timeframe_weeks=payload.get("timeframe_weeks"),
        active=True,
    )
    db.add(g); db.commit(); db.refresh(g)
    return {"ok": True, "goal_id": g.id}

@app.get("/goals")
def get_goals(athlete_id: int, db: Session = Depends(get_db)):
    if Goal is None:
        raise HTTPException(status_code=501, detail="Goal model not available yet. Add it in models.py and restart.")
    g = (
        db.execute(
            select(Goal)
            .where(Goal.athlete_id == athlete_id, Goal.active == True)  # noqa: E712
            .order_by(Goal.created_at.desc())
        ).scalars().first()
    )
    return {
        "athlete_id": athlete_id,
        "goal": None if not g else {
            "id": g.id,
            "target_weight_kg": g.target_weight_kg,
            "target_bodyfat_pct": g.target_bodyfat_pct,
            "target_ftp_w": g.target_ftp_w,
            "goal_prompt": g.goal_prompt,
            "parsed_constraints": g.parsed_constraints,
            "timeframe_weeks": g.timeframe_weeks,
            "active": g.active,
            "created_at": g.created_at.isoformat() if getattr(g, "created_at", None) else None,
        },
    }


# ---------------- Metrics / Latest ----------------
@app.get("/metrics/latest")
def get_metrics_latest(athlete_id: int, db: Session = Depends(get_db)):
    if BodyMetrics is None:
        raise HTTPException(status_code=501, detail="BodyMetrics model not available.")

    def latest(field_name: str):
        col = getattr(BodyMetrics, field_name)
        row = (
            db.execute(
                select(BodyMetrics.date, col)
                .where(BodyMetrics.athlete_id == athlete_id, col.is_not(None))
                .order_by(BodyMetrics.date.desc())
                .limit(1)
            ).first()
        )
        return (row[0].isoformat(), row[1]) if row else (None, None)

    ftp_row = (
        db.execute(
            select(BodyMetrics.date, BodyMetrics.ftp_w, BodyMetrics.ftp_source)
            .where(BodyMetrics.athlete_id == athlete_id, BodyMetrics.ftp_w.is_not(None))
            .order_by(BodyMetrics.date.desc())
            .limit(1)
        ).first()
    )
    if ftp_row:
        ftp_d = ftp_row[0].isoformat()
        f = ftp_row[1]
        f_src = ftp_row[2] or "unknown"
    else:
        ftp_d, f, f_src = None, None, None

    w_d, w   = latest("weight_kg")
    bf_d, bf = latest("bodyfat_pct")
    vo2_d, v = latest("vo2max_mlkgmin")
    rhr_d, r = latest("resting_hr_bpm")

    dates = [d for d in (w_d, bf_d, vo2_d, rhr_d, ftp_d) if d]
    as_of = max(dates) if dates else None

    return {
        "athlete_id": athlete_id,
        "as_of": as_of,
        "metrics": {
            "weight_kg": w,
            "bodyfat_pct": bf,
            "vo2max_mlkgmin": v,
            "resting_hr_bpm": r,
            "ftp_w": f,
        },
        "dates": {
            "weight_kg": w_d,
            "bodyfat_pct": bf_d,
            "vo2max_mlkgmin": vo2_d,
            "resting_hr_bpm": rhr_d,
            "ftp_w": ftp_d,
        },
        "provenance": {
            "ftp_w": {"source": f_src, "updated_at": ftp_d}
        },
    }


# ---------------- Apple Health ZIP import ----------------
@app.post("/apple_health/import")
async def apple_health_import(
    athlete_id: int = Form(...),
    file: UploadFile = File(...),
    since_days: int = Form(180),
    db: Session = Depends(get_db),
):
    if BodyMetrics is None:
        raise HTTPException(status_code=501, detail="BodyMetrics model not available.")

    # open zip
    try:
        file.file.seek(0)
        zf = zipfile.ZipFile(file.file)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="invalid_zip")

    cutoff = (date.today() - timedelta(days=since_days))

    # locate export.xml
    xml_name = next((n for n in zf.namelist() if n.endswith("export.xml")), None)
    if not xml_name:
        raise HTTPException(status_code=400, detail="export_xml_not_found")

    def _parse_apple_date_to_day(s: str) -> date:
        # "2025-10-04 07:15:28 +0100"
        return date.fromisoformat(s.split(" ")[0])

    day_metrics: Dict[date, Dict[str, float]] = {}
    workouts: List[Dict] = []
    rec_count = 0
    work_count = 0

    # parse with iterparse
    with zf.open(xml_name, "r") as fh:
        for event, elem in ET.iterparse(fh):
            tag = elem.tag.split("}")[-1]

            if tag == "Record":
                rtype = elem.attrib.get("type")
                unit = (elem.attrib.get("unit") or "").lower()
                val = _to_float(elem.attrib.get("value"))
                end_dt = elem.attrib.get("endDate") or elem.attrib.get("creationDate") or elem.attrib.get("startDate")
                if val is None or not end_dt:
                    elem.clear(); continue
                d = _parse_apple_date_to_day(end_dt)
                if d < cutoff:
                    elem.clear(); continue

                bucket = day_metrics.setdefault(d, {})
                if rtype == "HKQuantityTypeIdentifierBodyMass":
                    if unit in ("lb", "lbs"):
                        val = val * 0.45359237
                    bucket["weight_kg"] = val
                elif rtype == "HKQuantityTypeIdentifierBodyFatPercentage":
                    if val <= 1.0:
                        val = val * 100.0
                    bucket["bodyfat_pct"] = val
                elif rtype == "HKQuantityTypeIdentifierVO2Max":
                    bucket["vo2max_mlkgmin"] = val
                elif rtype == "HKQuantityTypeIdentifierRestingHeartRate":
                    bucket["resting_hr_bpm"] = val
                elif rtype == "HKQuantityTypeIdentifierCyclingFunctionalThresholdPower":
                    bucket["ftp_w"] = val

                rec_count += 1
                if rec_count % 100000 == 0:
                    log.info(f"Apple import: parsed {rec_count} records… unique days={len(day_metrics)}")
                elem.clear()

            elif tag == "Workout":
                wtype = (elem.attrib.get("workoutActivityType") or "")
                end = elem.attrib.get("endDate")
                dur = _to_float(elem.attrib.get("duration"))
                dur_unit = (elem.attrib.get("durationUnit") or "").lower()
                if not end or dur is None:
                    elem.clear(); continue
                d = _parse_apple_date_to_day(end)
                if d < cutoff:
                    elem.clear(); continue

                if "cycling" in wtype.lower():
                    duration_min = dur if "min" in dur_unit else dur * 60.0
                    tss = int(round(duration_min * 0.75))  # rough eTSS
                    workouts.append({
                        "date": d, "sport": "bike",
                        "duration_min": int(round(duration_min)),
                        "tss": tss
                    })
                    work_count += 1
                    if work_count % 500 == 0:
                        log.info(f"Apple import: parsed {work_count} workouts…")
                elem.clear()

    # upsert BodyMetrics per day
    for d, vals in day_metrics.items():
        existing = db.execute(
            select(BodyMetrics).where(BodyMetrics.athlete_id == athlete_id, BodyMetrics.date == d)
        ).scalars().first()
        if existing:
            for k, v in vals.items():
                setattr(existing, k, v)
        else:
            db.add(BodyMetrics(athlete_id=athlete_id, date=d, **vals))

    # add Activities for cycling workouts (if Activity model exists)
    if Activity is not None:
        for w in workouts:
            db.add(Activity(
                athlete_id=athlete_id,
                date=w["date"],
                sport=w["sport"],
                duration_min=w["duration_min"],
                tss=w["tss"],
            ))

    db.commit()

    # refresh Athlete snapshot from latest day
    a = db.get(Athlete, athlete_id)
    if a:
        latest = db.execute(
            select(BodyMetrics)
            .where(BodyMetrics.athlete_id == athlete_id)
            .order_by(BodyMetrics.date.desc())
        ).scalars().first()
        if latest:
            if latest.ftp_w: a.ftp_w = latest.ftp_w
            if latest.resting_hr_bpm: a.rhr = latest.resting_hr_bpm
            if latest.vo2max_mlkgmin: a.vo2max = latest.vo2max_mlkgmin
            if latest.weight_kg: a.weight_kg = latest.weight_kg
        db.commit()

    log.info(f"Apple import done: days={len(day_metrics)}, workouts={len(workouts)}")
    return {"ok": True, "metrics_days_imported": len(day_metrics), "workouts_imported": len(workouts)}
