from fastapi import APIRouter, Query, HTTPException
import requests

router = APIRouter(prefix="/weather", tags=["weather"])  # /weather/...

@router.get("/today")
def weather_today(lat: float = Query(...), lon: float = Query(...)):
    try:
        # Open‑Meteo: daily min/max/precip/wind, current temp
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,wind_speed_10m"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max"
            "&timezone=auto"
        )
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        js = r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"weather_fetch_failed: {e}")

    curr = (js.get("current") or {})
    daily = (js.get("daily") or {})
    out = {
        "provider": "open-meteo",
        "current": {
            "temp_c": curr.get("temperature_2m"),
            "wind_kph": curr.get("wind_speed_10m"),
        },
        "today": {
            "tmax_c": (daily.get("temperature_2m_max") or [None])[0],
            "tmin_c": (daily.get("temperature_2m_min") or [None])[0],
            "precip_prob": (daily.get("precipitation_probability_max") or [None])[0],
            "wind_max_kph": (daily.get("wind_speed_10m_max") or [None])[0],
        },
    }
    return out
