import time, pandas as pd
from utils.strava_client import get_activities
from utils.db import read_sql, df_to_sql

def last_ts_epoch():
    df = read_sql("select max(ts) as last from activities")
    if df is None or df.empty or pd.isna(df.iloc[0]["last"]):
        return None
    return int(pd.Timestamp(df.iloc[0]["last"]).timestamp())

def normalize(acts):
    rows = []
    for a in acts:
        rows.append({
            "source":"strava",
            "activity_id": a.get("id"),
            "ts": pd.to_datetime(a.get("start_date")),
            "type": a.get("type"),
            "name": a.get("name"),
            "distance_km": (a.get("distance") or 0)/1000.0,
            "moving_time_sec": a.get("moving_time"),
            "elapsed_time_sec": a.get("elapsed_time"),
            "avg_power": a.get("average_watts"),
            "max_power": a.get("max_watts"),
            "avg_hr": a.get("average_heartrate"),
            "max_hr": a.get("max_heartrate"),
            "elevation_gain_m": a.get("total_elevation_gain"),
            "calories": a.get("kilojoules"),
            "tss": None, "ifactor": None, "ftp": None
        })
    return pd.DataFrame(rows)

def main():
    since = last_ts_epoch()
    acts = get_activities(after_epoch=since, per_page=100)
    if not acts:
        print("No new Strava activities.")
        return
    df = normalize(acts)
    df_to_sql(df, "activities")
    print(f"Inserted {len(df)} activities.")

if __name__ == "__main__":
    main()
