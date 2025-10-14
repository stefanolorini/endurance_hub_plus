#!/usr/bin/env bash
set -euo pipefail
API="${API:-https://endurance-hub-plus.onrender.com}"

check() {
  local url="$1"
  echo "→ $url"
  local code
  code=$(curl -sS -o /tmp/smoke_body -w "%{http_code}" "$url" || true)
  echo "  HTTP $code"
  if [ "$code" != "200" ]; then
    echo "  Body (first 300 chars):"
    head -c 300 /tmp/smoke_body 2>/dev/null || true
    echo
  fi
}

echo "API=$API"
check "$API/metrics/latest?athlete_id=1"
check "$API/training/plan?athlete_id=1&indoor=false"
check "$API/weather/today?lat=48.21&lon=16.37"
check "$API/dashboard/today?athlete_id=1"
check "$API/metrics/history?athlete_id=1&days=30"
check "$API/activities/list?athlete_id=1&limit=5"
