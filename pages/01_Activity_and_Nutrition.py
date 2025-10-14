# FILE CONTENT: pages/01_Activity_and_Nutrition.py
import requests, pandas as pd, streamlit as st

API = "https://endurance-hub-plus.onrender.com"
ATHLETE_ID = 1

st.title("Training & Nutrition Overview")

# Helper: round to nearest 0.5 for display (VO₂, RHR, Weight, FTP)
def round05(x):
    return None if x is None else round(x * 2) / 2

# Recent activities
st.subheader("Recent activities")
r = requests.get(f"{API}/activities/list", params={"athlete_id": ATHLETE_ID, "limit": 30})
items = r.json().get("items", [])
if items:
    df = pd.DataFrame(items)
    for c in ("duration_min","tss"):
        if c in df: df[c] = pd.to_numeric(df[c], errors="coerce")
    st.dataframe(df)
else:
    st.info("No activities yet.")

# Physiology charts (90d)
st.subheader("Physiology — last 90 days")
fields = "weight_kg,vo2max_mlkgmin,resting_hr_bpm,ftp_w"
r = requests.get(f"{API}/metrics/history", params={"athlete_id": ATHLETE_ID, "days": 90, "fields": fields})
h = r.json().get("items", [])
if h:
    hd = pd.DataFrame(h)
    if "date" in hd: hd = hd.set_index("date")
    for col in ["weight_kg","vo2max_mlkgmin","resting_hr_bpm","ftp_w"]:
        if col in hd: hd[col] = hd[col].apply(round05)
    for col in ["weight_kg","vo2max_mlkgmin","resting_hr_bpm","ftp_w"]:
        if col in hd:
            st.line_chart(hd[col].dropna())
else:
    st.info("No historical metrics yet.")

# Nutrition logs (30d)
st.subheader("Nutrition — last 30 days")
r = requests.get(f"{API}/nutrition/logs", params={"athlete_id": ATHLETE_ID, "days": 30})
logs = r.json().get("items", [])
if logs:
    nd = pd.DataFrame(logs)
    st.dataframe(nd)
    if "date" in nd and "kcal" in nd:
        st.line_chart(nd.set_index("date")["kcal"].dropna())
else:
    st.info("No nutrition logs found.")
