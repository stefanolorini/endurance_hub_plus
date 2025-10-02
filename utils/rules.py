import pandas as pd

def adapt(plan_row, daily, load_row, weather_row):
    decisions = []

    # Readiness
    if daily is not None and not daily.empty and len(daily) >= 7:
        d = daily.iloc[-1]
        med7_hrv = daily["hrv_ms"].rolling(7).median().iloc[-1]
        med7_rhr = daily["rhr"].rolling(7).median().iloc[-1]
        hrv_drop = (d["hrv_ms"] - med7_hrv)
        rhr_rise = (d["rhr"] - med7_rhr)
        sleep_ok = d.get("sleep_duration_min", 0) >= 420
        if (hrv_drop < -15 and rhr_rise > 5) or (not sleep_ok):
            decisions.append(("Readiness", "Reduce", "Low HRV/high RHR or poor sleep"))

    # Load (TSB)
    if load_row and "TSB" in load_row and load_row["TSB"] is not None:
        if load_row["TSB"] < -10:
            decisions.append(("Load", "Reduce", "TSB < -10"))
        elif load_row["TSB"] > 5:
            decisions.append(("Load", "Progress", "TSB > +5"))

    # Weather
    if weather_row:
        if (weather_row.get("precip_prob",0) > 0.7) or (weather_row.get("wind_kph",0) > 30):
            decisions.append(("Weather", "Swap", "Bad weather: indoor or swap"))

    # Weight trend (2‑week slope)
    if daily is not None and "weight_kg" in daily.columns and len(daily)>=14:
        w2 = daily["weight_kg"].iloc[-1]
        w0 = daily["weight_kg"].iloc[-14]
        weekly_rate = (w2 - w0)/2.0
        if weekly_rate < -0.7:
            decisions.append(("Nutrition", "Increase kcal", "Weight loss >0.7 kg/week"))
        elif weekly_rate > -0.2 and plan_row.get("nutrition_day","")!="maintenance":
            decisions.append(("Nutrition", "Reduce kcal modestly", "Weight loss <0.2 kg/week"))

    if not decisions:
        return {"rule":"None", "decision":"Maintain", "reason":"No flags"}

    for r in decisions:
        if r[1]=="Reduce":
            return {"rule":r[0], "decision":r[1], "reason":r[2]}
    for r in decisions:
        if r[1]=="Swap":
            return {"rule":r[0], "decision":r[1], "reason":r[2]}
    return {"rule":decisions[0][0], "decision":"Progress", "reason":decisions[0][2]}
