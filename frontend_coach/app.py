# frontend_coach/app.py
import os
import json
from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Endurance Hub — Coach", layout="wide")

# ------------------------------ Config ------------------------------
def _cfg(name: str, default=None):
    # Prefer env var locally; fall back to Streamlit secrets if present.
    v = os.getenv(name)
    if v:
        return v
    try:
        return st.secrets[name]
    except Exception:
        return default

API_BASE_URL = _cfg("API_BASE_URL", "https://endurance-hub-plus.onrender.com")
API_KEY      = _cfg("API_KEY")

HEADERS = {"Accept": "application/json"}
if API_KEY:
    HEADERS["x-api-key"] = API_KEY


# ------------------------------ HTTP helpers ------------------------------
@st.cache_data(ttl=30)
def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict:
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    r = requests.get(url, params=params or {}, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=10)
def _post_json(path: str, payload: Optional[Dict[str, Any]] = None) -> Dict:
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    r = requests.post(url, json=payload or {}, headers=HEADERS, timeout=40)
    r.raise_for_status()
    return r.json()

# Multipart (for Apple ZIP)
def _post_multipart(path: str, files: Dict[str, Any], data: Dict[str, Any]) -> Dict:
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    # Do NOT set Content-Type; requests sets multipart boundary.
    headers = {k: v for k, v in HEADERS.items() if k.lower() != "content-type"}
    r = requests.post(url, files=files, data=data, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()

# ------------------------------ API wrappers ------------------------------

def get_athlete(athlete_id: int) -> Dict:
    return _get(f"/athlete/{athlete_id}")

def patch_athlete(athlete_id: int, payload: Dict[str, Any]) -> Dict:
    _get.clear()  # invalidate cache for athlete
    url = f"{API_BASE_URL.rstrip('/')}/athlete/{athlete_id}"
    r = requests.patch(url, json=payload, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return r.json()

def get_metrics_latest(athlete_id: int) -> Dict:
    return _get("/metrics/latest", params={"athlete_id": athlete_id})

def get_training_plan(athlete_id: int) -> Dict:
    return _get("/training/plan", params={"athlete_id": int(athlete_id)})

def get_nutrition_today(athlete_id: int) -> Dict:
    return _get("/nutrition/today", params={"athlete_id": athlete_id})

def post_goal(payload: Dict[str, Any]) -> Dict:
    _post_json.clear()
    return _post_json("/goals", payload)

def apple_import_zip(athlete_id: int, zip_bytes: bytes, since_days: int = 180) -> Dict:
    files = {"file": ("export.zip", zip_bytes, "application/zip")}
    data = {"athlete_id": str(athlete_id), "since_days": str(since_days)}
    return _post_multipart("/apple_health/import", files=files, data=data)

# ------------------------------ Sidebar ------------------------------
with st.sidebar:
    st.markdown("### Settings")
    base_default = API_BASE_URL
    API_BASE_URL = st.text_input("API Base URL", value=API_BASE_URL)
    if API_BASE_URL != base_default:
        _get.clear(); _post_json.clear()
    athlete_ids_raw = st.text_input("Athlete IDs (comma-separated)", value="1")
    athlete_ids: List[int] = []
    for part in athlete_ids_raw.split(","):
        part = part.strip()
        if part.isdigit():
            athlete_ids.append(int(part))
    st.caption(f"Using API key: {'set' if API_KEY else 'not set'}")

st.title("Coach Dashboard")
TAB_OVERVIEW, TAB_ATHLETE, TAB_GOALS, TAB_IMPORT, TAB_ADMIN = st.tabs([
    "Overview", "Athlete", "Goals", "Import", "Admin"
])

# ------------------------------ Overview ------------------------------
with TAB_OVERVIEW:
    rows = []
    for aid in athlete_ids or [1]:
        try:
            m = get_metrics_latest(aid)
            plan = get_training_plan(aid)
            week = plan.get("microcycle", [])
            planned_tss = sum(int(s.get("tss", 0) or 0) for s in week)
            metrics = m.get("metrics") or {}
            as_of = m.get("as_of")
            rows.append({
                "athlete_id": aid,
                "as_of": as_of,
                "weight_kg": metrics.get("weight_kg"),
                "bodyfat_%": metrics.get("bodyfat_pct"),
                "VO2max": metrics.get("vo2max_mlkgmin"),
                "RHR": metrics.get("resting_hr_bpm"),
                "FTP": metrics.get("ftp_w"),
                "planned_week_TSS": planned_tss,
            })
        except Exception as e:
            rows.append({"athlete_id": aid, "error": str(e)})
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

# ------------------------------ Athlete detail ------------------------------
with TAB_ATHLETE:
    aid = st.selectbox("Select athlete", options=(athlete_ids or [1]))
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("Snapshot & Edit")
        try:
            a = get_athlete(aid)
            st.json(a)
            with st.expander("Edit core fields"):
                ftp_w = st.number_input("FTP (W)", value=float(a.get("ftp_w") or 0.0), step=5.0)
                vo2  = st.number_input("VO2max", value=float(a.get("vo2max") or 0.0), step=0.5)
                rhr  = st.number_input("RHR (bpm)", value=float(a.get("rhr") or 0.0), step=1.0)
                wt   = st.number_input("Weight (kg)", value=float(a.get("weight_kg") or 0.0), step=0.1)
                hcm  = st.number_input("Height (cm)", value=float(a.get("height_cm") or 0.0), step=0.5)
                age  = st.number_input("Age", value=int(a.get("age") or 35), step=1)
                if st.button("Save changes", use_container_width=True):
                    out = patch_athlete(aid, {
                        "ftp_w": ftp_w, "vo2max": vo2, "rhr": rhr,
                        "weight_kg": wt, "height_cm": hcm, "age": age
                    })
                    st.success(out)
                    _get.clear()
        except Exception as e:
            st.error(f"Failed to load athlete {aid}: {e}")
    with c2:
        st.subheader("Week Plan")
        try:
            plan = get_training_plan(aid)
            week = plan.get("microcycle", [])
            if week:
                cols = ["date","title","sport","duration_min","tss","target_power_w","details"]
                st.dataframe(pd.DataFrame(week)[[c for c in cols if c in week[0]]], use_container_width=True)
            else:
                st.info("No weekly plan.")
        except Exception as e:
            st.warning(f"Plan unavailable: {e}")
        st.subheader("Today Nutrition")
        try:
            n = get_nutrition_today(aid)
            st.dataframe(pd.DataFrame([n.get("targets", {})]), use_container_width=True)
        except Exception as e:
            st.info("Nutrition endpoint unavailable")

# ------------------------------ Goals ------------------------------
with TAB_GOALS:
    aid = st.selectbox("Athlete for goal", options=(athlete_ids or [1]), key="goal_aid")
    c1, c2 = st.columns([2,1])
    with c1:
        goal_prompt = st.text_area("Goal prompt (free text)", placeholder="e.g., Lose 3kg in 10 weeks while improving FTP by 3%")
        target_weight = st.number_input("Target weight (kg)", value=0.0, step=0.1)
        target_bf = st.number_input("Target bodyfat %", value=0.0, step=0.1)
        target_ftp = st.number_input("Target FTP (W)", value=0.0, step=5.0)
        timeframe = st.number_input("Timeframe (weeks)", value=6, step=1)
        if st.button("Save goal", type="primary"):
            payload = {
                "athlete_id": aid,
                "target_weight_kg": (target_weight or None),
                "target_bodyfat_pct": (target_bf or None),
                "target_ftp_w": (target_ftp or None),
                "goal_prompt": goal_prompt or None,
                "parsed_constraints": None,
                "timeframe_weeks": int(timeframe),
            }
            try:
                res = post_goal(payload)
                st.success(res)
            except Exception as e:
                st.error(f"Failed to save goal: {e}")
    with c2:
        st.info("Goals are stored as the active goal for the athlete. You can add a read-back in the Coach app once we expose /goals GET for the active goal (already present).")

# ------------------------------ Import (Apple Health ZIP) ------------------------------
with TAB_IMPORT:
    aid = st.selectbox("Athlete for import", options=(athlete_ids or [1]), key="import_aid")
    since = st.number_input("Since days", min_value=7, value=180, step=1)
    up = st.file_uploader("Apple Health export.zip", type=["zip"], accept_multiple_files=False)
    if up and st.button("Upload & Import", use_container_width=True):
        try:
            res = apple_import_zip(aid, up.getvalue(), since_days=int(since))
            st.success(res)
            _get.clear()
        except Exception as e:
            st.error(f"Import failed: {e}")

# ------------------------------ Admin ------------------------------
with TAB_ADMIN:
    st.caption("Diagnostics")
    try:
        env = _get("/debug/env")
        st.json(env)
    except Exception:
        st.write("/debug/env not enabled or gated.")
    st.caption("Raw API responses")
    with st.expander("metrics/latest raw"):
        try: st.code(json.dumps(get_metrics_latest((athlete_ids or [1])[0]), indent=2))
        except Exception as e: st.write(str(e))
