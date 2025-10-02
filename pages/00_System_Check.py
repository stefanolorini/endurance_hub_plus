import streamlit as st, pandas as pd
from sqlalchemy import text
from utils.db import ENGINE
from utils.app_guard import safe_query

st.set_page_config(page_title="System Check", layout="wide")
st.title("🔎 System Check")

# 1) Secrets present?
needed = ["DATABASE_URL","ATHLETE_ID","GARMIN_USERNAME","GARMIN_PASSWORD"]
present = {k: (k in st.secrets and bool(st.secrets[k])) for k in needed}
st.subheader("Secrets")
st.table(pd.DataFrame([present]))

# 2) Can we list tables?
def run_info():
    with ENGINE.begin() as c:
        return pd.read_sql(text("""
          select table_name
          from information_schema.tables
          where table_schema='public'
          order by table_name
        """), c)
tables = safe_query(run_info, empty_ok=True, error_message="DB connection failed.")
st.subheader("Public tables found")
st.dataframe(tables)

required = {"plan", "activities", "daily_metrics"}
have = set(tables["table_name"].astype(str)) if not tables.empty else set()
missing = required - have
if missing:
    st.warning("Missing required tables: " + ", ".join(sorted(missing)) + ". "
               "Run your schema.sql in Supabase, upload a plan CSV, and/or ingest Garmin.")
else:
    st.success("All required tables exist ✔︎")

# 3) Quick row counts
def q1():
    with ENGINE.begin() as c: return pd.read_sql(text("select count(*) as plan_rows from public.plan"), c)
def q2():
    with ENGINE.begin() as c: return pd.read_sql(text("select count(*) as activities from public.activities"), c)
def q3():
    with ENGINE.begin() as c: return pd.read_sql(text("select count(*) as daily_metrics from public.daily_metrics"), c)

st.subheader("Row counts")
col1,col2,col3 = st.columns(3)
with col1: st.write(safe_query(q1, empty_ok=True))
with col2: st.write(safe_query(q2, empty_ok=True))
with col3: st.write(safe_query(q3, empty_ok=True))
