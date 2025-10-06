import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.getenv("API_KEY", "")
DEFAULT_LAT = float(os.getenv("HOME_LAT", "48.2082"))
DEFAULT_LON = float(os.getenv("HOME_LON", "16.3738"))
CORS_ALLOW_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ALLOW_ORIGINS", "http://localhost:3000,http://localhost:8501"
).split(",")]
