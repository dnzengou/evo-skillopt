#!/usr/bin/env bash
# deploy_vercel.sh — ship the Clow landing + dashboard + api to Vercel.
#
# What it does:
#   1. Assembles a clean deploy dir (no SkillOpt Python, no Rust, no bots/*)
#   2. Runs `vercel --prod` on the assembled dir
#
# Why the assembly step:
#   This SkillOpt repo also contains index.html (the SkillOpt project page),
#   Python scripts, the Rust backend, and sample bots. Deploying the whole
#   repo to Vercel would serve unrelated files and inflate the deploy.
#   We ship only what the landing needs.
#
# Prerequisites (one-time):
#   npm i -g vercel
#   vercel login
#   vercel link                         # links this dir to the Vercel project
#   vercel env add AIRTABLE_API_KEY     # + AIRTABLE_BASE_ID, AIRTABLE_TABLE
#                                       # + (optional) GTM_ENGINE_URL, GTM_ENGINE_TOKEN
#
# Usage:
#   ./scripts/deploy_vercel.sh            # deploys to production
#   PREVIEW=1 ./scripts/deploy_vercel.sh  # deploys a preview URL

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$ROOT/.vercel-deploy"

echo "▸ Assembling deploy dir at $STAGE"
rm -rf "$STAGE"
mkdir -p "$STAGE/api"

# HTML — landing serves at /, use-cases at /use-cases, dashboard at /dashboard
cp "$ROOT/clow_landing.html" "$STAGE/clow_landing.html"
cp "$ROOT/use_cases.html"    "$STAGE/use_cases.html"
cp "$ROOT/dashboard.html"    "$STAGE/dashboard.html"

# Vercel routing + security headers
cp "$ROOT/vercel.json" "$STAGE/vercel.json"

# Edge Functions
cp "$ROOT/api/waitlist.js" "$STAGE/api/waitlist.js"
cp "$ROOT/api/og.js"       "$STAGE/api/og.js"

# @vercel/og is only needed for api/og.js — declare it so Vercel installs it
cat > "$STAGE/package.json" <<'JSON'
{
  "name": "clow-landing",
  "private": true,
  "type": "module",
  "dependencies": {
    "@vercel/og": "^0.6.0"
  }
}
JSON

echo "▸ Deploy dir ready. Contents:"
ls -1 "$STAGE"
echo ""

echo "▸ Running vercel deploy…"
cd "$STAGE"

if [ -n "${PREVIEW:-}" ]; then
  vercel
else
  vercel --prod
fi

echo ""
echo "✓ Deploy complete."
echo "  Landing:   https://<your-domain>/"
echo "  Use cases: https://<your-domain>/use-cases"
echo "  Dashboard: https://<your-domain>/dashboard  (add auth before exposing!)"
echo "  Waitlist:  POST https://<your-domain>/api/waitlist"
echo "  OG image:  https://<your-domain>/api/og"
