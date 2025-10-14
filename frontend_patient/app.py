from components.quicklog_section import render_quicklog_section
import os
import json
from datetime import date
from typing import Any, Dict, Optional

import pandas as pd
import requests
import streamlit as st
from components.overview_section import render_overview_section


st.set_page_config(page_title="Endurance Hub — Patient", layout="wide")

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


# ------------------------------ Helpers ------------------------------
@st.cache_data(ttl=30)
def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict:
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    r = requests.get(url, params=params or {}, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

# ------------------------------ API wrappers ------------------------------

def get_metrics_latest(athlete_id: int) -> Dict:
    return _get("/metrics/latest", params={"athlete_id": athlete_id})

def get_training_plan(athlete_id: int) -> Dict:
    return _get("/training/plan", params={"athlete_id": athlete_id})

def get_nutrition_today(athlete_id: int) -> Dict:
    return _get("/nutrition/today", params={"athlete_id": athlete_id})

# ------------------------------ UI ------------------------------
with st.sidebar:
    st.markdown("### Settings")
    st.caption("Backend API")
    st.text_input("API Base URL", key="api_base", value=API_BASE_URL)
    if st.session_state.api_base != API_BASE_URL:
        API_BASE_URL = st.session_state.api_base
        _get.clear()

    athlete_id = st.number_input("Athlete ID", min_value=1, value=1, step=1)
    colR1, colR2 = st.columns(2)
    with colR1:
        if st.button("Refresh", use_container_width=True):
            _get.clear()
    with colR2:
        st.write("")
        st.caption(date.today().isoformat())

st.title("Today")

# --- Overview (activities + physiology + nutrition) ---
athlete_id = st.session_state.get('athlete_id', 1)
render_overview_section(athlete_id)

TAB_TODAY, TAB_TRENDS, TAB_HELP = st.tabs(["Today", "Trends (soon)", "Help"])  

# ------------------------------ Today Tab ------------------------------
with TAB_TODAY:
    col1, col2 = st.columns([1, 1])
    # Metrics
    with col1:
        st.subheader("Physiology — Latest")
        try:
            m = get_metrics_latest(athlete_id)
            metrics = m.get("metrics") or {}
            dates = m.get("dates") or {}
            grid = st.columns(5)
            grid[0].metric("Weight (kg)", metrics.get("weight_kg"), help=f"as of {dates.get('weight_kg')}")
            grid[1].metric("Bodyfat %", metrics.get("bodyfat_pct"), help=f"as of {dates.get('bodyfat_pct')}")
            grid[2].metric("VO2max", metrics.get("vo2max_mlkgmin"), help=f"as of {dates.get('vo2max_mlkgmin')}")
            grid[3].metric("RHR (bpm)", metrics.get("resting_hr_bpm"), help=f"as of {dates.get('resting_hr_bpm')}")
            grid[4].metric("FTP (W)", metrics.get("ftp_w"), help=f"as of {dates.get('ftp_w')}")
            st.caption(f"Athlete {athlete_id} • as of {m.get('as_of')}")
        except requests.HTTPError as e:
            st.error(f"Failed to load metrics: {e}")
        except Exception as e:
            st.warning(f"Metrics unavailable: {e}")

    # Nutrition
    with col2:
        st.subheader("Nutrition — Today Targets")
        try:
            n = get_nutrition_today(athlete_id)
            targets = n.get("targets") or {}
            df = pd.DataFrame([targets])
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.warning(f"Nutrition endpoint unavailable: {e}")

    # Training Plan — focus on today
    st.subheader("Training — Today")
    try:
        plan = get_training_plan(athlete_id)
        today_iso = date.today().isoformat()
        sessions = plan.get("microcycle", [])
        today_sessions = [s for s in sessions if s.get("date") == today_iso]
        if not today_sessions:
            st.caption("No explicit session for today; showing week plan")
            today_df = pd.DataFrame(sessions)
        else:
            today_df = pd.DataFrame(today_sessions)
        if not today_df.empty:
            cols = [c for c in ["date","title","sport","duration_min","tss","target_power_w","intensity","details"] if c in 
today_df.columns]
            st.dataframe(today_df[cols], use_container_width=True)
        else:
            st.info("No plan available yet.")
    except Exception as e:
        st.warning(f"Training endpoint unavailable: {e}")

# ------------------------------ Trends Tab (placeholder) ------------------------------
with TAB_TRENDS:
    st.info("Coming soon: weight/bodyfat, VO2max, RHR and FTP trends with weekly training load.")

# ------------------------------ Help Tab ------------------------------
with TAB_HELP:
    st.write("If something looks off, pull to refresh (sidebar) or try again later.")
    st.write("Contact your coach for goal updates or training changes.")
\n\n\n# --- Quick Log (keep physiology fresh) ---\nathlete_id = st.session_state.get('athlete_id', 1)\nrender_quicklog_section(athlete_id)\n