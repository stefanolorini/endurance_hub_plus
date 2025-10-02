import os, requests
from dotenv import load_dotenv
load_dotenv()
CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

def _refresh_access_token():
    r = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN
    }, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]

def get_activities(after_epoch=None, per_page=100):
    token = _refresh_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    params = {"per_page": per_page}
    if after_epoch: params["after"] = after_epoch
    r = requests.get("https://www.strava.com/api/v3/athlete/activities", headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json()
