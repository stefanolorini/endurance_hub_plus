#!/usr/bin/env bash
set -euo pipefail
API=${API:-https://endurance-hub-plus.onrender.com}
echo "API=$API"

check() {
  local url="$1"
  echo "→ $url"
  # Save body to a tmp file and capture HTTP code
  local tmp="$(mktemp)"
  local code
  code=$(curl -sS -w '%{http_code}' -o "$tmp" "$url") || { echo "curl failed"; rm -f "$tmp"; return 1; }
  echo "  HTTP $code"
  if [ "$code" != "200" ]; then
    echo "  Body (first 300 chars):"
    head -c 300 "$tmp" | sed 's/[[:cntrl:]]//g'
    echo
    rm -f "$tmp"
    return 1
  fi
  # Validate JSON
  if ! python3 -m json.tool < "$tmp" >/dev/null 2>&1; then
    echo "  ❌ Invalid JSON. Body (first 300 chars):"
    head -c 300 "$tmp" | sed 's/[[:cntrl:]]//g'
    echo
    rm -f "$tmp"
    return 1
  fi
  rm -f "$tmp"
}

check "$API/metrics/latest?athlete_id=1"
check "$API/training/plan?athlete_id=1&indoor=false"
check "$API/weather/today?lat=48.21&lon=16.37"
check "$API/dashboard/today?athlete_id=1"

echo "✅ Smoke passed"
