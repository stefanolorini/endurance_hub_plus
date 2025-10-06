import streamlit as st
import requests
import datetime as dt

st.set_page_config(page_title="Athlete App (MVP)", layout="wide")
st.title("Athlete App (MVP)")

# ----- Config -----
BACKEND_DEFAULT = "http://127.0.0.1:8000"
with st.sidebar:
    st.header("Settings")
    backend = st.text_input("Backend URL", BACKEND_DEFAULT)
    athlete_id = st.number_input("Athlete ID", min_value=1, value=1, step=1)
    st.caption("Tip: leave as default while testing locally.")

# ----- Helpers -----
def get(path, **params):
    r = requests.get(f"{backend}{path}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def post(path, json=None, files=None, data=None, **params):
    r = requests.post(f"{backend}{path}", params=params, json=json, files=files, data=data, timeout=60)
    r.raise_for_status()
    return r.json()

# ----- Live snapshot -----
col1, col2, col3 = st.columns([1.2, 1, 1])
with col1:
    st.subheader("Latest metrics")
    try:
        latest = get("/metrics/latest", athlete_id=int(athlete_id))
        m = latest.get("metrics", {})
        d = latest.get("dates", {})
        ftp_prov = (latest.get("provenance") or {}).get("ftp_w", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Weight (kg)", m.get("weight_kg"), d.get("weight_kg"))
        c2.metric("Bodyfat (%)", m.get("bodyfat_pct"), d.get("bodyfat_pct"))
        c3.metric("VO2max (ml/kg/min)", m.get("vo2max_mlkgmin"), d.get("vo2max_mlkgmin"))
        c4, c5 = st.columns(2)
        c4.metric("Resting HR (bpm)", m.get("resting_hr_bpm"), d.get("resting_hr_bpm"))
        c5.metric("FTP (W)", m.get("ftp_w"), ftp_prov.get("updated_at"))
        if ftp_prov:
            st.caption(f"FTP source: **{ftp_prov.get('source')}** (as of {ftp_prov.get('updated_at')})")
    except Exception as e:
        st.error(f"Failed to load latest metrics: {e}")

with col2:
    st.subheader("Today’s nutrition")
    try:
        nt = get("/nutrition/today", athlete_id=int(athlete_id))
        targ = nt.get("targets", {})
        st.metric("Calories", f"{targ.get('kcal')} kcal")
        st.metric("Protein", f"{targ.get('protein_g')} g")
        st.metric("Carbs", f"{targ.get('carbs_g') or '—'} g")
        st.metric("Fat", f"{targ.get('fat_g') or '—'} g")
        st.caption(f"Date: {nt.get('date')}")
    except Exception as e:
        st.error(f"Failed to load nutrition targets: {e}")

with col3:
    st.subheader("Fatigue snapshot")
    try:
        plan = get("/training/plan", athlete_id=int(athlete_id))
        ctx = plan.get("context", {})
        st.metric("7-day TSS", ctx.get("fatigue_7d_tss", 0))
        st.metric("Indoor?", "Yes" if ctx.get("indoor") else "No")
        b = plan.get("block", {})
        st.caption(f"Block: {b.get('weeks','?')}w + {b.get('recovery_weeks','?')}w rec • Recovery week: {b.get('is_recovery_week')}")
    except Exception as e:
        st.error(f"Failed to load fatigue / block info: {e}")

st.divider()

# ----- Today’s session + week schedule -----
st.subheader("Training — today & this week")
try:
    plan = get("/training/plan", athlete_id=int(athlete_id))
    micro = plan.get("microcycle", [])
    iso_today = dt.date.today().isoformat()
    today_row = None
    for s in micro:
        if s.get("date") == iso_today:
            today_row = s; break
    if not today_row and micro:
        today_row = micro[0]  # fallback

    if today_row:
        st.markdown(f"### Today: **{today_row.get('title','')}**")
        st.write(f"{today_row.get('details','')}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Duration", f"{int(today_row.get('duration_min',0))} min")
        c2.metric("Intensity", today_row.get("intensity_factor","—"))
        c3.metric("TSS", today_row.get("tss","—"))
        tw = today_row.get("target_power_w")
        c4.metric("Target watts", f"{int(tw[0])}-{int(tw[1])} W" if tw else "—")

    # Weekly table
    import pandas as pd
    rows = []
    for s in micro:
        rows.append({
            "Date": s.get("date"),
            "Title": s.get("title"),
            "Type": s.get("sport"),
            "Intensity": s.get("intensity_factor"),
            "Duration (min)": s.get("duration_min"),
            "TSS": s.get("tss"),
            "Target W": f"{int(s['target_power_w'][0])}-{int(s['target_power_w'][1])}" if s.get("target_power_w") else "",
            "Notes": s.get("details","")
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"Failed to load training plan: {e}")

st.divider()

# ----- Optional: free-text goal → plan preview -----
st.subheader("Plan preview from a free-text goal (optional)")
colA, colB = st.columns([2,1])
with colA:
    # Try to prefill with the active goal’s prompt if available
    default_goal = "Boost cycling FTP in 6 weeks; keep long endurance Saturdays; 6-7h/week."
    try:
        g = requests.get(f"{backend}/goals", params={"athlete_id": int(athlete_id)}, timeout=10).json()
        gp = (g or {}).get("goal", {}).get("goal_prompt") or default_goal
    except Exception:
        gp = default_goal
    goal_text = st.text_area("Describe your goal", value=gp, height=120)
with colB:
    weeks = st.number_input("Plan length (weeks)", min_value=4, max_value=24, value=6, step=1)
    start_date = st.date_input("Start date", value=dt.date.today())

if st.button("Generate plan preview"):
    try:
        payload = {"goal_text": goal_text, "weeks": int(weeks), "start_date": str(start_date)}
        plan_prev = post("/plan/preview", json=payload, athlete_id=int(athlete_id))
        st.success("Plan preview generated.")
        st.json(plan_prev.get("summary", {}))
        st.write("**Nutrition targets**")
        st.json(plan_prev.get("nutrition", {}))
        st.write("**Supplements**")
        st.json(plan_prev.get("supplements", []))
        st.write("**Adaptation rules**")
        st.json(plan_prev.get("adaptation_rules", []))
    except Exception as e:
        st.error(f"Plan preview failed: {e}")

st.divider()

# ----- Apple Health import (quick data refresh) -----
st.subheader("Apple Health ZIP import (optional)")
upload = st.file_uploader("Upload export.zip from Apple Health (compressed)", type=["zip"])
since_days = st.slider("Import last N days", min_value=30, max_value=365, value=180, step=30)
if upload and st.button("Import"):
    try:
        files = {"file": ("export.zip", upload.getvalue(), "application/zip")}
        data = {"athlete_id": str(int(athlete_id)), "since_days": str(int(since_days))}
        res = post("/apple_health/import", files=files, data=data)
        st.success(f"Imported: {res.get('metrics_days_imported')} days, {res.get('workouts_imported')} workouts")
    except Exception as e:
        st.error(f"Import failed: {e}")

st.caption("This MVP is for personal testing. We’ll add auth and persistence later.")
