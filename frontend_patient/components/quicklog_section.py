import requests, streamlit as st
from datetime import date

def render_quicklog_section(athlete_id: int):
    api = st.secrets.get("API_BASE_URL", "https://endurance-hub-plus.onrender.com")
    key = st.secrets.get("API_KEY")

    st.subheader("Quick log — Weight / RHR / VO₂ / FTP")

    with st.form("quicklog_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1, value=None, placeholder="e.g. 75.5")
            rhr = st.number_input("Resting HR (bpm)", min_value=0, step=1, value=None, placeholder="e.g. 54")
        with col2:
            vo2 = st.number_input("VO₂max (ml/kg/min)", min_value=0.0, step=0.1, value=None, placeholder="e.g. 59.5")
            ftp = st.number_input("FTP (W)", min_value=0, step=1, value=None, placeholder="e.g. 300")
        the_date = st.date_input("Date", value=date.today())
        submitted = st.form_submit_button("Save")

    if submitted:
        payload = {
            "date": the_date.isoformat(),
            "weight_kg": float(weight) if weight is not None else None,
            "resting_hr_bpm": int(rhr) if rhr is not None else None,
            "vo2max_mlkgmin": float(vo2) if vo2 is not None else None,
            "ftp_w": int(ftp) if ftp is not None else None,
        }
        payload = {k:v for k,v in payload.items() if v is not None}
        if len(payload) == 1:  # only date present
            st.warning("Enter at least one metric.")
            return
        try:
            headers = {"x-api-key": key} if key else {}
            r = requests.post(f"{api}/metrics/log", params={"athlete_id": athlete_id}, json=payload, headers=headers, timeout=15)
            r.raise_for_status()
            st.success("Saved!")
        except Exception as e:
            st.error(f"Save failed: {e}")
