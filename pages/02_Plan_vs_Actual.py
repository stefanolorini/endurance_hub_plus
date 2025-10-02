import streamlit as st, pandas as pd
from utils.db import read_sql

st.title("📝 Plan vs Actual")

df_plan = read_sql("select * from plan order by date asc")
df_act = read_sql("select date_trunc('day', ts) as date, sum(moving_time_sec)/3600 as hours, sum(distance_km) as km, sum(calories) as kcal from activities group by 1 order by 1")

st.subheader("Planned sessions")
st.dataframe(df_plan)

st.subheader("Actual per day")
st.dataframe(df_act)

if not df_plan.empty and not df_act.empty:
    merged = df_plan[["date","session_type","duration_hr"]].merge(df_act, on="date", how="left")
    merged["delta_hours"] = merged["hours"].fillna(0) - merged["duration_hr"].fillna(0)
    st.subheader("Gap (last 30 days)")
    st.dataframe(merged.tail(30))
