import os, datetime as dt
from dotenv import load_dotenv
from garminconnect import Garmin

load_dotenv()
USERNAME = os.getenv("GARMIN_USERNAME")
PASSWORD = os.getenv("GARMIN_PASSWORD")

def fetch_daily(date: dt.date):
    api = Garmin(USERNAME, PASSWORD)
    api.login()
    summary = api.get_stats_and_body(date.isoformat())
    sleep = api.get_sleep_data(date.isoformat())
    hrv = api.get_hrv_data(date.isoformat())
    api.logout()
    return {"summary": summary, "sleep": sleep, "hrv": hrv}
