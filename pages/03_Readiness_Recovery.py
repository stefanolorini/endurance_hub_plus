import streamlit as st, pandas as pd, plotly.express as px
from utils.db import read_sql

st.title("🛌 Readiness & Recovery")

df_daily = read_sql("select * from daily_metrics order by date asc")
if df_daily.empty:
    st.info("No daily metrics yet.")
else:
    st.plotly_chart(px.line(df_daily, x="date", y=["hrv_ms","rhr","sleep_duration_min","weight_kg","vo2max"]), use_container_width=True)

    st.markdown("**Red flag heuristics:**")
    st.markdown("- HRV ↓ > 15% from 7‑day median **and** RHR ↑ > 5 bpm")
    st.markdown("- Sleep < 7h last night")
