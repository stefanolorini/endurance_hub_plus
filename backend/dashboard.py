import streamlit as st
import requests

st.set_page_config(page_title="Health Dashboard", layout="centered")
st.title("Today’s Metrics")

backend = st.text_input("Backend URL", "http://127.0.0.1:8000")
athlete_id = st.number_input("Athlete ID", value=1, step=1)

def fetch_latest(base, aid: int):
    url = f"{base}/metrics/latest"
    r = requests.get(url, params={"athlete_id": aid}, timeout=10)
    r.raise_for_status()
    return r.json()

if st.button("Load"):
    try:
        data = fetch_latest(backend, int(athlete_id))
        st.subheader("Raw response")
        st.json(data)

        m = data.get("metrics", {})
        d = data.get("dates", {})
        p = (data.get("provenance") or {}).get("ftp_w", {})

        st.subheader("Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Weight (kg)", m.get("weight_kg"))
        c2.metric("Bodyfat (%)", m.get("bodyfat_pct"))
        c3.metric("VO2max (ml/kg/min)", m.get("vo2max_mlkgmin"))

        c4, c5 = st.columns(2)
        c4.metric("Resting HR (bpm)", m.get("resting_hr_bpm"))
        c5.metric("FTP (W)", m.get("ftp_w"))

        st.caption(f"Dates → weight: {d.get('weight_kg')}, bodyfat: {d.get('bodyfat_pct')}, vo2: {d.get('vo2max_mlkgmin')}, rhr: {d.get('resting_hr_bpm')}, ftp: {d.get('ftp_w')}")
        if p:
            st.caption(f"FTP source: {p.get('source')} • updated_at: {p.get('updated_at')}")
    except Exception as e:
        st.error(str(e))
