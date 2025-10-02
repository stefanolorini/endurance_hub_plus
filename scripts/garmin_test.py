# scripts/garmin_test.py
import os
from garminconnect import Garmin
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

user = os.getenv("GARMIN_USERNAME")
pwd  = os.getenv("GARMIN_PASSWORD")
if not user or not pwd:
    raise SystemExit("Set GARMIN_USERNAME and GARMIN_PASSWORD in your .env")

print("Logging in to Garmin…")
g = Garmin(user, pwd)
g.login()   # if you have 2FA, you may be prompted once

acts = g.get_activities(0, 5)  # latest 5
print(f"Fetched {len(acts)} activities")
for a in acts:
    print(f"- {a.get('activityId')} | {a.get('activityType',{}).get('typeKey')} | {a.get('startTimeLocal')} | {a.get('distance')} m")
# scripts/garmin_test.py
import os
from garminconnect import Garmin

user = os.getenv("GARMIN_USERNAME")
pwd  = os.getenv("GARMIN_PASSWORD")
if not user or not pwd:
    raise SystemExit("Set GARMIN_USERNAME and GARMIN_PASSWORD in your .env")

print("Logging in to Garmin…")
g = Garmin(user, pwd)
g.login()   # if you have 2FA, it may prompt in the terminal the first time

acts = g.get_activities(0, 5)  # latest 5
print(f"Fetched {len(acts)} activities")
for a in acts:
    print(f"- {a.get('activityId')} | {a.get('activityType',{}).get('typeKey')} | {a.get('startTimeLocal')} | {a.get('distance')} m")

