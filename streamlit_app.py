import streamlit as st
import httpx
import pandas as pd
from datetime import datetime

API_URL = "http://127.0.0.1:8000"
ATHLETE_ID = 1
LAT, LON = 48.2082, 16.3738

st.set_page_config(page_title="Endurance Hub Dashboard", layout="wide")
st.title("🏋️‍♂️ Athlete Dashboard")

# Sidebar controls
refresh_rate = st.sidebar.slider("Auto‑refresh interval (seconds)", 10, 120, 30)
manual_refresh = st.sidebar.button("🔄 Refresh Now")

# Cache or reload function
@st.cache_data(ttl=refresh_rate)
def fetch_dashboard():
    r = httpx.get(
        f"{API_URL}/dashboard/today",
        headers={"x-api-key": "dev-key-123"},
        params={"athlete_id": ATHLETE_ID, "lat": LAT, "lon": LON},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()

if manual_refresh:
    st.cache_data.clear()

data = fetch_dashboard()

# Tabs for navigation
tabs = st.tabs(["🏋️ Session", "🥗 Nutrition", "🌦 Weather", "💤 Readiness"])

with tabs[0]:
    st.header("Today's Session")
    st.metric("Title", data['session']['title'])
    st.metric("Duration (min)", data['session']['duration_min'])
    st.write(data['session']['details'])

with tabs[1]:
    st.header("Nutrition Targets")
    st.json(data['nutrition'])

with tabs[2]:
    st.header("Weather")
    st.json(data['weather'])

with tabs[3]:
    st.header("Readiness Snapshot")
    st.json(data['readiness'])

st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
