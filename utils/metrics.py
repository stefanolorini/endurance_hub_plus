import pandas as pd

def estimate_tss(row):
    if pd.notnull(row.get("tss")):
        return row["tss"]
    secs = row.get("moving_time_sec", 0) or 0
    return (secs/3600.0) * 50  # rough

def rolling_load(df_activities: pd.DataFrame):
    df = df_activities.copy()
    if df.empty:
        return df
    df["tss_est"] = df.apply(estimate_tss, axis=1)
    df = df.sort_values("ts")
    df["ATL_7d"] = df.set_index("ts")["tss_est"].rolling("7D").sum().values
    df["CTL_42d"] = (df.set_index("ts")["tss_est"].rolling("42D").sum() / 7.0).values
    df["TSB"] = df["CTL_42d"].shift(1) - df["ATL_7d"].shift(1)
    return df
