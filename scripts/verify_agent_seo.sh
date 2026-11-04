#!/usr/bin/env bash
# verify_agent_seo.sh — prove every agent-discovery surface is live.
#
# Runs through the agent-SEO stack a buyer / crawler / LLM would hit:
# repo-root files (local), live-worker endpoints (if $WORKER reachable),
# and the docs site (if $SITE reachable). Exits 0 iff every probed
# surface answered correctly.
#
# Usage:
#   ./scripts/verify_agent_seo.sh                             # local repo only
#   WORKER=http://localhost:9000 ./scripts/verify_agent_seo.sh
#   WORKER=https://your-app.fly.dev SITE=https://dnzengou.github.io/evo-skillopt \
#     ./scripts/verify_agent_seo.sh
set -u

WORKER=${WORKER:-}
SITE=${SITE:-}

ROOT=$(cd "$(dirname "$0")/.." && pwd)
fail=0

ok()   { printf "  ✓ %s\n" "$1"; }
bad()  { printf "  ✗ %s\n" "$1"; fail=$((fail + 1)); }
hr()   { printf "\n== %s ==\n" "$1"; }

probe_file() {
  local label=$1 path=$2
  if [ -f "$ROOT/$path" ] && [ -s "$ROOT/$path" ]; then
    ok "$label  ($path)"
  else
    bad "$label  ($path missing or empty)"
  fi
}

probe_url() {
  local label=$1 url=$2 want=${3:-200}
  local code
  code=$(curl -s -o /dev/null -m 5 -w "%{http_code}" "$url" 2>/dev/null || echo 000)
  if [ "$code" = "$want" ]; then
    ok "$label  $url ($code)"
  else
    bad "$label  $url (got $code, expected $want)"
  fi
}

probe_json() {
  local label=$1 url=$2
  if curl -sf -m 5 "$url" 2>/dev/null | python3 -c 'import json,sys; json.load(sys.stdin)' >/dev/null 2>&1; then
    ok "$label  $url (valid JSON)"
  else
    bad "$label  $url (not valid JSON or unreachable)"
  fi
}

probe_yaml() {
  local label=$1 url=$2
  if curl -sf -m 5 "$url" 2>/dev/null | python3 -c 'import yaml,sys; yaml.safe_load(sys.stdin)' >/dev/null 2>&1; then
    ok "$label  $url (valid YAML)"
  else
    bad "$label  $url (not valid YAML or unreachable)"
  fi
}

hr "Repo-root agent-SEO files"
probe_file "AGENTS.md                 " "AGENTS.md"
probe_file "llms.txt                  " "llms.txt"
probe_file "llms-full.txt             " "llms-full.txt"
probe_file ".well-known/agents.json   " ".well-known/agents.json"
probe_file ".well-known/openapi.yaml  " ".well-known/openapi.yaml"
probe_file "CITATION.cff              " "CITATION.cff"
probe_file "GTM.md                    " "GTM.md"
probe_file "docs/AI_SEO.md            " "docs/AI_SEO.md"
probe_file "docs/robots.txt           " "docs/robots.txt"

hr "Repo-root JSON-LD in README.md"
if grep -q '"@type": "SoftwareApplication"' "$ROOT/README.md"; then
  ok "README.md carries SoftwareApplication JSON-LD"
else
  bad "README.md missing SoftwareApplication JSON-LD"
fi

hr "Repo-root schema validation"
if python3 -c 'import json; json.load(open("'"$ROOT"'/.well-known/agents.json"))' 2>/dev/null; then
  ok ".well-known/agents.json parses as JSON"
else
  bad ".well-known/agents.json does not parse as JSON"
fi
if python3 -c 'import yaml; yaml.safe_load(open("'"$ROOT"'/.well-known/openapi.yaml"))' 2>/dev/null; then
  ok ".well-known/openapi.yaml parses as YAML"
else
  bad ".well-known/openapi.yaml does not parse as YAML"
fi

if [ -n "$WORKER" ]; then
  hr "Live worker discovery ($WORKER)"
  probe_url  "service card            " "$WORKER/"                          200
  probe_url  "health                  " "$WORKER/health"                    200
  probe_url  "AGENTS.md               " "$WORKER/AGENTS.md"                 200
  probe_url  "llms.txt                " "$WORKER/llms.txt"                  200
  probe_url  "llms-full.txt           " "$WORKER/llms-full.txt"             200
  probe_url  "openapi (alias)         " "$WORKER/openapi.yaml"              200
  probe_json "service card is JSON    " "$WORKER/"
  probe_json "agents.json is JSON     " "$WORKER/.well-known/agents.json"
  probe_yaml "openapi.yaml is YAML    " "$WORKER/.well-known/openapi.yaml"
  probe_url  "unknown path 404s       " "$WORKER/does-not-exist"            404
else
  hr "Live worker discovery"
  printf "  (set WORKER=<url> to probe the running service)\n"
fi

if [ -n "$SITE" ]; then
  hr "Docs site discovery ($SITE)"
  probe_url  "home                    " "$SITE/"                            200
  probe_url  "llms.txt                " "$SITE/llms.txt"                    200
  probe_url  "llms-full.txt           " "$SITE/llms-full.txt"               200
  probe_url  "AGENTS.md               " "$SITE/AGENTS.md"                   200
  probe_url  "agents.json             " "$SITE/.well-known/agents.json"     200
  probe_url  "openapi.yaml            " "$SITE/.well-known/openapi.yaml"    200
  probe_url  "robots.txt              " "$SITE/robots.txt"                  200
else
  hr "Docs site discovery"
  printf "  (set SITE=<url> to probe the published MkDocs site)\n"
fi

echo ""
if [ "$fail" -eq 0 ]; then
  echo "✓ agent-SEO surface is healthy"
  exit 0
else
  echo "✗ $fail check(s) failed — agents/crawlers will see a hole"
  exit 1
fi
