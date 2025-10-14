import requests, pandas as pd, streamlit as st

def round05(x):
    return None if x is None else round(x * 2) / 2

def _get_json(api_base, path, **params):
    r = requests.get(f"{api_base}{path}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def render_overview_section(athlete_id: int):
    api = st.secrets.get("API_BASE_URL", "https://endurance-hub-plus.onrender.com")

    st.subheader("Overview")

    # Recent activities
    with st.container():
        st.markdown("**Recent activities**")
        try:
            data = _get_json(api, "/activities/list", athlete_id=athlete_id, limit=30)
            items = data.get("items", [])
            if items:
                df = pd.DataFrame(items)
                for c in ("duration_min","tss"):
                    if c in df: df[c] = pd.to_numeric(df[c], errors="coerce")
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No activities yet.")
        except Exception as e:
            st.error(f"Activities error: {e}")

    # Physiology charts (90d)
    with st.container():
        st.markdown("**Physiology — last 90 days**")
        try:
            fields = "weight_kg,vo2max_mlkgmin,resting_hr_bpm,ftp_w"
            h = _get_json(api, "/metrics/history", athlete_id=athlete_id, days=90, fields=fields).get("items", [])
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
        except Exception as e:
            st.error(f"Physiology error: {e}")

    # Nutrition logs (30d)
    with st.container():
        st.markdown("**Nutrition — last 30 days**")
        try:
            logs = _get_json(api, "/nutrition/logs", athlete_id=athlete_id, days=30).get("items", [])
            if logs:
                nd = pd.DataFrame(logs)
                st.dataframe(nd, use_container_width=True)
                if "date" in nd and "kcal" in nd:
                    st.line_chart(nd.set_index("date")["kcal"].dropna())
            else:
                st.info("No nutrition logs found.")
        except Exception as e:
            st.error(f"Nutrition error: {e}")
