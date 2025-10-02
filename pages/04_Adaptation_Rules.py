import streamlit as st, pandas as pd
from utils.db import read_sql
from utils.rules import adapt

st.title("🧠 Adaptation Rules")

df_plan = read_sql("select * from plan order by date asc")
df_daily = read_sql("select * from daily_metrics order by date asc")
df_weather = read_sql("select * from weather order by date asc")
df_act = read_sql("select * from activities order by ts asc")

if df_plan.empty:
    st.info("Upload plan first in Admin.")
else:
    today = pd.Timestamp.now().normalize().date()
    plan_today = df_plan[df_plan["date"]==pd.Timestamp(today)]
    if plan_today.empty:
        st.info("No planned session for today.")
    else:
        load_row = df_act.tail(1).to_dict("records")[0] if not df_act.empty else {}
        weather_row = df_weather[df_weather["date"]==pd.Timestamp(today)].to_dict("records")
        weather_row = weather_row[0] if weather_row else {}
        decision = adapt(plan_today.iloc[0].to_dict(), df_daily, load_row, weather_row)
        st.json(decision)
