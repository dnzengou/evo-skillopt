#!/usr/bin/env bash
# smoke.sh — health probe for a locally-running evo-skillopt worker.
#
# Usage:
#   ./scripts/smoke.sh                                           # localhost default
#   WORKER=https://your-app.fly.dev ./scripts/smoke.sh           # remote
#   WORKER=http://localhost:9000 API_TOKEN=xyz ./scripts/smoke.sh
set -u

WORKER=${WORKER:-http://localhost:9000}
TOKEN=${API_TOKEN:-${WORKER_TOKEN:-}}

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

auth_probe() {
  local name=$1 url=$2
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
    -H "Authorization: Bearer $TOKEN" "$url" 2>/dev/null || echo "000")
  case "$code" in
    200|204|400|500)
      printf "  ✓ %-20s %s (%s — reachable, auth accepted)\n" "$name" "$url" "$code" ;;
    401|403)
      printf "  ! %-20s %s (%s — token mismatch)\n" "$name" "$url" "$code"
      fail=$((fail + 1)) ;;
    *)
      printf "  ✗ %-20s %s (%s)\n" "$name" "$url" "$code"
      fail=$((fail + 1)) ;;
  esac
}

echo "== evo-skillopt worker smoke =="
probe "health" "$WORKER/health"

if [ -n "$TOKEN" ]; then
  echo ""
  echo "== Authenticated probe (POST /train reachability) =="
  # Sends a minimal body to confirm auth + routing without triggering a real training run.
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
    -X POST "$WORKER/train" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"bot_id":"smoke/probe"}' 2>/dev/null || echo "000")
  case "$code" in
    200|400|500)
      printf "  ✓ %-20s %s (%s — reachable, auth accepted)\n" "train" "$WORKER/train" "$code" ;;
    401|403)
      printf "  ! %-20s %s (%s — token mismatch)\n" "train" "$WORKER/train" "$code"
      fail=$((fail + 1)) ;;
    *)
      printf "  ✗ %-20s %s (%s)\n" "train" "$WORKER/train" "$code"
      fail=$((fail + 1)) ;;
  esac
else
  echo ""
  echo "(set WORKER_TOKEN or API_TOKEN to also probe POST /train)"
fi

echo ""
if [ "$fail" -eq 0 ]; then
  echo "✓ all green"
  exit 0
else
  echo "✗ $fail check(s) failed"
  exit 1
fi
