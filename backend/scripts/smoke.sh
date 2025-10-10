#!/usr/bin/env bash
set -euo pipefail
API=${API:-https://endurance-hub-plus.onrender.com}
echo "API=$API"
curl -sS "$API/metrics/latest?athlete_id=1" | python3 -m json.tool >/dev/null
curl -sS "$API/training/plan?athlete_id=1&indoor=false" | python3 -m json.tool >/dev/null
curl -sS "$API/weather/today?lat=48.21&lon=16.37" | python3 -m json.tool >/dev/null
curl -sS "$API/dashboard/today?athlete_id=1" | python3 -m json.tool >/dev/null
echo "✅ Smoke passed"
