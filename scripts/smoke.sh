#!/usr/bin/env bash
# smoke.sh — health probe for the Clow backend stack
# Usage:
#   ./scripts/smoke.sh                    # localhost defaults
#   GTM=https://gtm-engine.fly.dev ./scripts/smoke.sh
set -u

GTM=${GTM:-http://localhost:8080}
SEC=${SEC:-http://localhost:8081}
EVO=${EVO:-http://localhost:8082}
WORKER=${WORKER:-http://localhost:9000}
TOKEN=${API_TOKEN:-dev-token-change-me}

fail=0
probe() {
  local name=$1 url=$2
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
  if [ "$code" = "200" ]; then
    printf "  ✓ %-20s %s (200)\n" "$name" "$url"
  else
    printf "  ✗ %-20s %s (%s)\n" "$name" "$url" "$code"
    fail=$((fail + 1))
  fi
}

echo "== Clow backend smoke =="
probe "gtm-engine"      "$GTM/health"
probe "security-agent"  "$SEC/health"
probe "evo-metaclaw"    "$EVO/health"
probe "skillopt-worker" "$WORKER/health"

echo ""
echo "== Authenticated smoke =="
auth_probe() {
  local name=$1 url=$2
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
    -H "Authorization: Bearer $TOKEN" "$url" 2>/dev/null || echo "000")
  case "$code" in
    200|204) printf "  ✓ %-20s %s (%s)\n" "$name" "$url" "$code" ;;
    401|403) printf "  ! %-20s %s (%s — token mismatch?)\n" "$name" "$url" "$code"; fail=$((fail + 1)) ;;
    *)       printf "  ✗ %-20s %s (%s)\n" "$name" "$url" "$code"; fail=$((fail + 1)) ;;
  esac
}
auth_probe "gtm accounts"    "$GTM/accounts"
auth_probe "gtm forecast"    "$GTM/pipeline/forecast"
auth_probe "sec findings"    "$SEC/findings"
auth_probe "evo bots"        "$EVO/bots"

echo ""
echo "== Public leaderboard =="
probe "evo leaderboard"      "$EVO/leaderboard"

echo ""
if [ "$fail" -eq 0 ]; then
  echo "✓ all green"
  exit 0
else
  echo "✗ $fail check(s) failed"
  exit 1
fi
