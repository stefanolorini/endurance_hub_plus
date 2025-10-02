import streamlit as st, pandas as pd, plotly.express as px
from utils.db import read_sql
from utils.metrics import rolling_load

st.title("📊 Dashboard")

df_act = read_sql("select * from activities order by ts asc")
df_daily = read_sql("select * from daily_metrics order by date asc")

if df_act.empty and df_daily.empty:
    st.info("No data yet. Upload plan and connect data sources in Admin.")
else:
    if not df_act.empty:
        df_load = rolling_load(df_act)
        cols = st.columns(3)
        last_power = df_act.iloc[-1].get("avg_power", None)
        cols[0].metric("Last Ride Avg Power", f"{last_power:.0f}" if last_power else "—")
        cols[1].metric("ATL (7d)", f"{df_load.iloc[-1]['ATL_7d']:.0f}")
        cols[2].metric("CTL (42d, weekly)", f"{df_load.iloc[-1]['CTL_42d']:.0f}")
        st.plotly_chart(px.line(df_load, x="ts", y=["ATL_7d","CTL_42d","TSB"]), use_container_width=True)
    if not df_daily.empty:
        st.subheader("Readiness markers")
        st.plotly_chart(px.line(df_daily, x="date", y=["rhr","hrv_ms","sleep_duration_min","weight_kg","vo2max"]), use_container_width=True)
