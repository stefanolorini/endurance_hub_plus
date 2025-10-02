import requests, os
from dotenv import load_dotenv
load_dotenv()
LAT = float(os.getenv("HOME_LAT", "47.2692"))
LON = float(os.getenv("HOME_LON", "11.4041"))

def get_daily_weather():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=temperature_2m_max,precipitation_probability_mean,windspeed_10m_max&timezone=auto"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    j = r.json()
    out = []
    for i, date in enumerate(j["daily"]["time"]):
        out.append({
            "date": date,
            "temp_c": j["daily"]["temperature_2m_max"][i],
            "precip_prob": j["daily"]["precipitation_probability_mean"][i]/100.0,
            "wind_kph": j["daily"]["windspeed_10m_max"][i]
        })
    return out
