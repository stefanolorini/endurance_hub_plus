# scripts/fetch_garmin.py
import os, sys
from datetime import datetime, timedelta, date
from pathlib import Path

import pandas as pd
from sqlalchemy import text

# --- locate project root & .env, add to path ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# --- env & project imports ---
from utils.db import ENGINE  # uses DATABASE_URL from .env
from garminconnect import Garmin

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
START_DAYS = int(os.getenv("GARMIN_BACKFILL_DAYS", "45"))

ATHLETE_ID = os.getenv("ATHLETE_ID")
if not ATHLETE_ID:
    raise RuntimeError("ATHLETE_ID not set in .env")

GARMIN_USER = os.getenv("GARMIN_USERNAME")
GARMIN_PASS = os.getenv("GARMIN_PASSWORD")
if not GARMIN_USER or not GARMIN_PASS:
    raise RuntimeError("Set GARMIN_USERNAME and GARMIN_PASSWORD in .env")

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def login() -> Garmin:
    g = Garmin(GARMIN_USER, GARMIN_PASS)
    g.login()   # may prompt for 2FA the first time
    return g

def fetch_activities(g: Garmin, start_days: int = START_DAYS) -> pd.DataFrame:
    # latest N (Garmin paginates)
    acts = g.get_activities(0, 400)
    rows = []
    window_start = (datetime.now() - timedelta(days=start_days)).date()

    for a in acts:
        try:
            start_ts = pd.to_datetime(a.get("startTimeGMT") or a.get("startTimeLocal"))
            rows.append({
                "activity_id": str(a["activityId"]),
                "source": "garmin",
                "ts": start_ts,
                "type": a.get("activityType", {}).get("typeKey"),
                "name": a.get("activityName"),
                "distance_km": (a.get("distance") or 0) / 1000.0,
                "moving_time_sec": a.get("duration") or 0,
                "elapsed_time_sec": a.get("elapsedDuration") or 0,
                "avg_power": a.get("avgPower"),
                "max_power": a.get("maxPower"),
                "avg_hr": a.get("averageHR"),
                "max_hr": a.get("maxHR"),
                "elevation_gain_m": a.get("elevationGain") or 0,
                "calories": a.get("calories"),
                "tss": None,      # can compute later if you want
                "ifactor": None,
                "ftp": None,
            })
        except Exception as e:
            print("Skip activity due to parse error:", e)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.sort_values("ts")
    df = df[df["ts"].dt.date >= window_start]

    # add athlete id and coerce numerics (keeps temp table clean)
    df["athlete_id"] = ATHLETE_ID
    for c in ["distance_km","moving_time_sec","elapsed_time_sec","avg_power","max_power",
              "avg_hr","max_hr","elevation_gain_m","calories","tss","ifactor","ftp"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def fetch_daily_metrics(g: Garmin, start_days: int = 90) -> pd.DataFrame:
    start = (datetime.now() - timedelta(days=start_days)).date()
    end   = datetime.now().date()
    rows = []

    for d in pd.date_range(start, end, freq="D"):
        d_str = d.strftime("%Y-%m-%d")

        # Defaults
        sleep_min = None
        rhr = None
        hrv_ms = None
        vo2 = None

        try:
            sleep = g.get_sleep_data(d_str)
            if isinstance(sleep, dict):
                sleep_min = sleep.get("dailySleepDTO", {}).get("sleepTimeInMinutes")
        except Exception:
            pass

        try:
            wellness = g.get_wellness(d_str)
            rhr = wellness.get("restingHeartRate") if isinstance(wellness, dict) else None
        except Exception:
            pass

        try:
            hrv = g.get_hrv_data(d_str)  # not available to all accounts
            if isinstance(hrv, dict):
                hrv_ms = hrv.get("hrvSummary", {}).get("lastNightAvg")
        except Exception:
            pass

        try:
            stats = g.get_user_summary(d_str)
            vo2 = stats.get("vo2Max") if isinstance(stats, dict) else None
        except Exception:
            pass

        rows.append({
            "date": d.date(),
            "rhr": rhr,
            "hrv_ms": hrv_ms,
            "sleep_duration_min": sleep_min,
            "sleep_score": None,
            "body_battery": None,
            "vo2max": vo2,
            "weight_kg": None,            # prefer Apple Health for body comp
            "body_fat_pct": None,
            "pulse_wave_velocity_ms": None,
            "athlete_id": ATHLETE_ID,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    for c in ["rhr","hrv_ms","sleep_duration_min","sleep_score","body_battery",
              "vo2max","weight_kg","body_fat_pct","pulse_wave_velocity_ms"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def upsert_df(df: pd.DataFrame, table: str, unique_cols: list[str]) -> int:
    """
    Upsert df into target 'schema.table' (default schema 'public').
    Creates a temp table in the same schema, casts types in SELECT.
    """
    if df.empty:
        return 0

    # Parse schema.table
    if "." in table:
        schema, tbl = table.split(".", 1)
    else:
        schema, tbl = "public", table

    tmp = f"{tbl}_tmp_ingest"

    cols = list(df.columns)

    # Casts for Postgres
    numeric_cols = {
        "distance_km": "double precision",
        "moving_time_sec": "double precision",
        "elapsed_time_sec": "double precision",
        "avg_power": "double precision",
        "max_power": "double precision",
        "avg_hr": "double precision",
        "max_hr": "double precision",
        "elevation_gain_m": "double precision",
        "calories": "double precision",
        "tss": "double precision",
        "ifactor": "double precision",
        "ftp": "double precision",
        "rhr": "double precision",
        "hrv_ms": "double precision",
        "sleep_duration_min": "double precision",
        "sleep_score": "double precision",
        "body_battery": "double precision",
        "vo2max": "double precision",
        "weight_kg": "double precision",
        "body_fat_pct": "double precision",
        "pulse_wave_velocity_ms": "double precision",
    }

    select_cols = []
    for c in cols:
        if c == "athlete_id":
            select_cols.append("cast(athlete_id as uuid) as athlete_id")
        elif c in numeric_cols:
            select_cols.append(f"cast({c} as {numeric_cols[c]}) as {c}")
        else:
            select_cols.append(c)

    select_cols_sql = ", ".join(select_cols)
    cols_sql = ", ".join(cols)
    updates = ", ".join([f"{c}=EXCLUDED.{c}" for c in cols if c not in unique_cols])
    unique_cols_sql = ", ".join(unique_cols)

    with ENGINE.begin() as conn:
        # write temp in same schema
        df.to_sql(tmp, con=conn, if_exists="replace", index=False, schema=schema)

        sql = text(f"""
            insert into {schema}.{tbl} ({cols_sql})
            select {select_cols_sql} from {schema}.{tmp}
            on conflict ({unique_cols_sql}) do update set {updates};
            drop table {schema}.{tmp};
        """)
        conn.execute(sql)

    return len(df)

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
if __name__ == "__main__":
    g = login()

    # Activities → public.activities (unique: activity_id)
    acts = fetch_activities(g, START_DAYS)
    if not acts.empty:
        # reorder to match target table column order
        cols = ["athlete_id","source","activity_id","ts","type","name","distance_km",
                "moving_time_sec","elapsed_time_sec","avg_power","max_power","avg_hr",
                "max_hr","elevation_gain_m","calories","tss","ifactor","ftp"]
        acts = acts[cols]
        upsert_df(acts, "public.activities", ["activity_id"])
        print(f"Upserted {len(acts)} activities from Garmin.")
    else:
        print("No activities fetched.")

    # Daily metrics → public.daily_metrics (unique: athlete_id + date)
    dm = fetch_daily_metrics(g, 90)
    if not dm.empty:
        cols_dm = ["athlete_id","date","rhr","hrv_ms","sleep_duration_min","sleep_score",
                   "body_battery","vo2max","weight_kg","body_fat_pct","pulse_wave_velocity_ms"]
        dm = dm[cols_dm]
        upsert_df(dm, "public.daily_metrics", ["athlete_id","date"])
        print(f"Upserted {len(dm)} daily metric rows from Garmin.")
    else:
        print("No daily metrics fetched.")
