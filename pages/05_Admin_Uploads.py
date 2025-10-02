import streamlit as st, pandas as pd, datetime as dt
from utils.db import df_to_sql
from utils.apple_health_parser import parse_health_export

st.title("🗂️ Admin: Uploads & Imports")

st.header("Upload Plan CSV")
file1 = st.file_uploader("Plan CSV", type=["csv"], key="plan")
if file1 is not None:
    df = pd.read_csv(file1, parse_dates=["date"])
    df_to_sql(df, "plan")
    st.success(f"Uploaded {len(df)} plan rows.")

st.header("Upload Apple Health Export (.zip)")
file2 = st.file_uploader("Apple Health zip", type=["zip"], key="hk")
if file2 is not None:
    bytes_data = file2.read()
    df_daily = parse_health_export(bytes_data)
    if not df_daily.empty:
        keep_cols = [c for c in ["date","rhr","hrv_ms","weight_kg","body_fat_pct"] if c in df_daily.columns]
        df_daily = df_daily[keep_cols]
        df_to_sql(df_daily, "daily_metrics")
        st.success(f"Ingested {len(df_daily)} daily metric rows from Apple Health.")
    else:
        st.warning("No parsable metrics found in the export.")
        
        # === WEEKLY TEMPLATE → EXPAND TO DATES =======================================
import streamlit as st, pandas as pd
from datetime import timedelta, date
from utils.db import df_to_sql

st.header("📅 Weekly Template → Expand to Dates")

with st.expander("How it works", expanded=False):
    st.markdown("""
    Upload a weekly template **without dates**, then choose a **season start date** and **number of weeks**.
    The app will expand your template into calendar dates and write them into the `plan` table.

    **Template CSV required columns (case-insensitive):**
    - `week_in_block` — 1..N within your block (e.g., 1..3 for build; 4 for deload)
    - `day_order` — 1..7 (order within the week; not tied to Mon/Tue etc.)
    - `session_type`, `description`, `duration_hr`
    - `nutrition_day`, `kcal`, `protein_g`, `carbs_g`, `fat_g`, `supplements` (can be blank)
    """)

tpl_file = st.file_uploader("Weekly Template CSV (no dates)", type=["csv"], key="tplcsv")
colA, colB, colC = st.columns(3)
start_date = colA.date_input("Season start date", value=pd.to_datetime("today").date())
total_weeks = int(colB.number_input("Total weeks to generate", min_value=1, max_value=52, value=16, step=1))
pattern_str = colC.text_input("Block pattern (build,deload)", value="3,1", help="e.g., '3,1' means 3 build weeks + 1 deload week, repeated")

apply_btn = st.button("Generate dated plan from template")

def _expand_from_template(df_tpl: pd.DataFrame, start_date: date, total_weeks: int, pattern: list[int]) -> pd.DataFrame:
    # normalize headers
    df = df_tpl.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    # required cols
    req = ["week_in_block","day_order","session_type","description","duration_hr","nutrition_day","kcal","protein_g","carbs_g","fat_g","supplements"]
    for c in req:
        if c not in df.columns:
            df[c] = None
    # types
    df["week_in_block"] = pd.to_numeric(df["week_in_block"], errors="coerce").fillna(1).astype(int)
    df["day_order"] = pd.to_numeric(df["day_order"], errors="coerce").fillna(1).astype(int)
    for c in ["duration_hr","kcal","protein_g","carbs_g","fat_g"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Build a repeating block pattern (e.g., [1,1,1,0] for 3 build + 1 deload)
    # We will map 'week_in_block' values to week numbers in each cycle.
    # Example: pattern=[3,1] -> cycle length = 4, weeks labeled 1..3 build, 4 deload
    cycle_len = sum(pattern)
    # within each cycle, week_in_block should be 1..pattern[0] for build, then (pattern[0]+1)..cycle_len for deloads (if any)
    # We'll simply repeat the template rows while setting calendar dates.
    rows = []
    cur = pd.to_datetime(start_date).date()
    for w in range(total_weeks):
        # which week number inside this cycle (1-based)
        w_in_cycle = (w % cycle_len) + 1
        # set current week's Monday = start_date + w*7
        week_start = cur + timedelta(days=7*w)
        # take the template rows whose week_in_block equals:
        # - if w_in_cycle <= pattern[0] → treat as build week index w_in_cycle
        # - else → treat as deload index (w_in_cycle - pattern[0]) but most templates use week_in_block=4 for deload in 3:1
        target_week_in_block = w_in_cycle  # simplest: use exact number (1..cycle_len)
        dfw = df[df["week_in_block"] == target_week_in_block]
        if dfw.empty:
            # fallback: if deload template isn't provided, reuse last build week's template but we'll halve duration later
            dfw = df[df["week_in_block"] == 1]

        for _, r in dfw.iterrows():
            # day_order: 1..7 → date = week_start + (day_order-1)
            this_date = week_start + timedelta(days=int(r["day_order"])-1)
            out = {
                "date": pd.to_datetime(this_date),
                "session_type": r["session_type"],
                "description": r["description"],
                "duration_hr": r["duration_hr"],
                "nutrition_day": r["nutrition_day"],
                "kcal": r["kcal"],
                "protein_g": r["protein_g"],
                "carbs_g": r["carbs_g"],
                "fat_g": r["fat_g"],
                "supplements": r["supplements"],
            }
            # auto-deload tweak: if this is a deload week (w_in_cycle > pattern[0]), reduce duration by 30%
            if w_in_cycle > pattern[0] and pd.notnull(out["duration_hr"]):
                out["duration_hr"] = round(float(out["duration_hr"]) * 0.7, 2)
                out["description"] = (out["description"] or "") + " (deload: ~30% less duration)"
            rows.append(out)

    out_df = pd.DataFrame(rows)
    # ensure date is date (not datetime w/ tz)
    out_df["date"] = pd.to_datetime(out_df["date"]).dt.date
    # sort by date then day_order is implicit
    out_df = out_df.sort_values("date").reset_index(drop=True)
    return out_df

if apply_btn and tpl_file is not None:
    try:
        tpl = pd.read_csv(tpl_file)
        # parse block pattern like "3,1" → [3,1]
        patt = [int(x.strip()) for x in pattern_str.split(",") if x.strip().isdigit()]
        if not patt:
            patt = [3,1]
        expanded = _expand_from_template(tpl, start_date, total_weeks, patt)
        st.success(f"Generated {len(expanded)} dated rows across {total_weeks} weeks starting {start_date}.")
        st.dataframe(expanded.head(14))
        # write to DB
        df_to_sql(expanded, "plan")
        st.success("Inserted expanded plan into table 'plan'.")
    except Exception as e:
        st.error(f"Failed to generate plan: {e}")

