# frontend_coach/app.py
import os
from datetime import date
import requests
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Endurance Hub — Coach", layout="wide")

API_BASE_URL = (
    st.secrets.get("API_BASE_URL") if hasattr(st, "secrets") else os.getenv("API_BASE_URL")
) or "https://endurance-hub-plus.onrender.com"
API_KEY = (
    st.secrets.get("API_KEY") if hasattr(st, "secrets") else os.getenv("API_KEY")
)


def api_get(path, params=None):
    headers = {"x-api-key": API_KEY} if API_KEY else {}
    r = requests.get(f"{API_BASE_URL}{path}", params=params or {}, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()

st.title("Coach Dashboard")
athlete_id = st.sidebar.number_input("Athlete ID", min_value=1, value=1, step=1)

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("Physiology — Latest")
    try:
        data = api_get("/metrics/latest", params={"athlete_id": int(athlete_id)})
        m = data.get("metrics", {})
        d = data.get("dates", {})
        st.metric("Weight (kg)", m.get("weight_kg") or "–", delta=None)
        st.metric("Body Fat (%)", m.get("bodyfat_pct") or "–")
        st.metric("VO₂max (ml/kg/min)", m.get("vo2max_mlkgmin") or "–")
        st.metric("Resting HR (bpm)", m.get("resting_hr_bpm") or "–")
        st.metric("FTP (W)", m.get("ftp_w") or "–")
        st.caption(f"As of: {data.get('as_of') or '–'}")
    except Exception as e:
        st.error(f"Failed to load latest metrics: {e}")

with col2:
    st.subheader("This Week Plan")
    try:
        plan = api_get("/training/plan", params={"athlete_id": int(athlete_id)})
        rows = []
        for s in plan.get("microcycle", []):
            rows.append({
                "date": s.get("date"),
                "title": s.get("title"),
                "sport": s.get("sport"),
                "duration_min": s.get("duration_min"),
                "tss": s.get("tss"),
            })
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No sessions planned.")
    except Exception as e:
        st.error(f"Failed to load plan: {e}")

st.caption("Tip: Use the Patient app to log activities. Auto‑import (Garmin→Strava→webhook) lands in Sprint 3.")