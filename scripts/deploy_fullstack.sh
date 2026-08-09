#!/usr/bin/env bash
# deploy_fullstack.sh — sequenced deploy of the entire Clow stack.
#
# Order (each step is idempotent — safe to re-run):
#   1. Fly.io backend:  gtm-engine → security-agent → evo-metaclaw
#   2. Cross-service wiring (evo-metaclaw ← SKILLOPT_WORKER_URL if set)
#   3. Vercel landing:  clow_landing + use_cases + dashboard + api/*
#
# Prerequisites (one-time):
#   flyctl:  curl -L https://fly.io/install.sh | sh
#   vercel:  npm i -g vercel
#   Auth:    fly auth login  &&  vercel login  &&  vercel link
#
# Env vars this script consumes:
#   PREFIX=""                   # optional; prepended to Fly app names
#                                (e.g. PREFIX=clow- → app names "clow-gtm-engine" …)
#                                Fly app names are globally unique; use PREFIX if
#                                the defaults are taken.
#   FLY_REGION=ord              # default: ord (Chicago)
#   API_TOKEN=<shared>          # shared bearer token across all 3 services
#   SLACK_WEBHOOK=<optional>    # hot-lead + evo alerts
#   SKIP_FLY=1                  # skip backend, ship landing only
#   SKIP_VERCEL=1               # skip landing, ship backend only
#
# Usage:
#   API_TOKEN=$(openssl rand -hex 32) ./scripts/deploy_fullstack.sh
#   PREFIX=myco- API_TOKEN=abc123 ./scripts/deploy_fullstack.sh
#   SKIP_VERCEL=1 ./scripts/deploy_fullstack.sh    # backend only

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${PREFIX:-}"
FLY_REGION="${FLY_REGION:-ord}"
API_TOKEN="${API_TOKEN:-}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

GTM_APP="${PREFIX}gtm-engine"
SEC_APP="${PREFIX}security-agent"
EVO_APP="${PREFIX}evo-metaclaw"

log() { printf "\033[1;36m▸\033[0m %s\n" "$*"; }
ok()  { printf "\033[1;32m✓\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m✗\033[0m %s\n" "$*" >&2; }
die() { err "$*"; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "$1 not installed"; }

# ─── PRE-FLIGHT ────────────────────────────────────────────────────────
log "Pre-flight"
need git
[ -z "${SKIP_FLY:-}" ] && need fly
[ -z "${SKIP_VERCEL:-}" ] && need vercel

if [ -z "$API_TOKEN" ] && [ -z "${SKIP_FLY:-}" ]; then
  die "API_TOKEN is required. Generate one: export API_TOKEN=\$(openssl rand -hex 32)"
fi

# ─── FLY.IO BACKEND ────────────────────────────────────────────────────
deploy_fly() {
  local app="$1" dir="$2"
  log "Fly: $app"

  if ! fly apps list 2>/dev/null | grep -qE "^\s*$app\s"; then
    log "  app not found → fly apps create $app"
    fly apps create "$app" --org personal || die "fly apps create failed for $app"
  fi

  # Volume for SQLite (idempotent)
  if ! fly volumes list -a "$app" 2>/dev/null | grep -q "${app//-/_}_data\|data"; then
    log "  creating 1GB volume in $FLY_REGION"
    fly volumes create data --region "$FLY_REGION" -a "$app" --size 1 --yes || true
  fi

  # Secrets
  local secrets=(API_TOKEN="$API_TOKEN")
  [ -n "$SLACK_WEBHOOK" ] && secrets+=(SLACK_WEBHOOK="$SLACK_WEBHOOK")
  log "  setting ${#secrets[@]} secret(s)"
  fly secrets set -a "$app" --stage "${secrets[@]}" >/dev/null

  # Deploy
  log "  deploying from $dir"
  (cd "$dir" && fly deploy -a "$app" --remote-only --ha=false)
  ok "$app deployed → https://$app.fly.dev"
}

if [ -z "${SKIP_FLY:-}" ]; then
  cd "$ROOT/clow-agents/backend"

  deploy_fly "$GTM_APP" "gtm-engine"
  deploy_fly "$SEC_APP" "security-agent"
  deploy_fly "$EVO_APP" "evo-metaclaw"

  # Optional cross-service wiring
  if [ -n "${SKILLOPT_WORKER_URL:-}" ]; then
    log "Wiring evo-metaclaw → SkillOpt worker"
    fly secrets set -a "$EVO_APP" --stage \
      SKILLOPT_WORKER_URL="$SKILLOPT_WORKER_URL" \
      SKILLOPT_WORKER_TOKEN="${SKILLOPT_WORKER_TOKEN:-}" >/dev/null
    fly deploy -a "$EVO_APP" --remote-only --ha=false
  fi

  ok "Backend live: $GTM_APP · $SEC_APP · $EVO_APP"
  cd "$ROOT"
fi

# ─── VERCEL LANDING ────────────────────────────────────────────────────
if [ -z "${SKIP_VERCEL:-}" ]; then
  log "Vercel: landing + edge functions"

  # Wire the landing to gtm-engine (if it exists)
  if [ -z "${SKIP_FLY:-}" ]; then
    log "  setting GTM_ENGINE_URL + GTM_ENGINE_TOKEN in Vercel"
    printf "%s" "https://$GTM_APP.fly.dev" | vercel env add GTM_ENGINE_URL production --force 2>&1 | tail -3 || true
    printf "%s" "$API_TOKEN" | vercel env add GTM_ENGINE_TOKEN production --force 2>&1 | tail -3 || true
  fi

  "$ROOT/scripts/deploy_vercel.sh"
fi

# ─── VERIFY ────────────────────────────────────────────────────────────
if [ -z "${SKIP_FLY:-}" ]; then
  log "Smoke test (backend)"
  GTM="https://$GTM_APP.fly.dev" \
  SEC="https://$SEC_APP.fly.dev" \
  EVO="https://$EVO_APP.fly.dev" \
  API_TOKEN="$API_TOKEN" \
  "$ROOT/scripts/smoke.sh" || true
fi

ok "Deploy complete."
echo ""
echo "URLs:"
[ -z "${SKIP_FLY:-}" ] && {
  echo "  gtm-engine:     https://$GTM_APP.fly.dev/health"
  echo "  security-agent: https://$SEC_APP.fly.dev/health"
  echo "  evo-metaclaw:   https://$EVO_APP.fly.dev/leaderboard  (public)"
}
[ -z "${SKIP_VERCEL:-}" ] && {
  echo "  landing:        https://<your-domain>/"
  echo "  use-cases:      https://<your-domain>/use-cases"
  echo "  waitlist:       POST https://<your-domain>/api/waitlist"
}
