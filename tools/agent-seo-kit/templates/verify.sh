#!/usr/bin/env bash
# .agent-seo-verify.sh — probe this project's agent-SEO surface.
#
# Usage:
#   bash .agent-seo-verify.sh                                 # repo-local checks
#   SITE=https://{{owner}}.github.io/{{repo}} bash .agent-seo-verify.sh
set -u

ROOT=$(cd "$(dirname "$0")" && pwd)
SITE=${SITE:-}
fail=0

ok()  { printf "  \033[32m✓\033[0m %s\n" "$*"; }
bad() { printf "  \033[31m✗\033[0m %s\n" "$*"; fail=$((fail+1)); }

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
  if [ "$code" = "$want" ]; then ok "$label  $url ($code)"
  else bad "$label  $url (got $code, expected $want)"; fi
}

echo "== repo-root agent-SEO files =="
probe_file "AGENTS.md                  " "AGENTS.md"
probe_file "llms.txt                   " "llms.txt"
probe_file "llms-full.txt              " "llms-full.txt"
probe_file ".well-known/agents.json    " ".well-known/agents.json"
probe_file ".well-known/openapi.yaml   " ".well-known/openapi.yaml"
probe_file "CITATION.cff               " "CITATION.cff"
probe_file "robots.txt                 " "robots.txt"

echo ""
echo "== schema validation =="
if python3 -c 'import json; json.load(open("'"$ROOT"'/.well-known/agents.json"))' 2>/dev/null; then
  ok "agents.json parses as JSON"
else
  bad "agents.json does not parse as JSON"
fi
if python3 -c 'import yaml; yaml.safe_load(open("'"$ROOT"'/.well-known/openapi.yaml"))' 2>/dev/null; then
  ok "openapi.yaml parses as YAML"
else
  bad "openapi.yaml does not parse as YAML (install pyyaml to run this check)"
fi

if [ -n "$SITE" ]; then
  echo ""
  echo "== live site discovery ($SITE) =="
  probe_url "home       " "$SITE/"                             200
  probe_url "llms.txt   " "$SITE/llms.txt"                     200
  probe_url "llms-full  " "$SITE/llms-full.txt"                200
  probe_url "AGENTS.md  " "$SITE/AGENTS.md"                    200
  probe_url "agents.json" "$SITE/.well-known/agents.json"      200
  probe_url "openapi    " "$SITE/.well-known/openapi.yaml"     200
  probe_url "robots.txt " "$SITE/robots.txt"                   200
fi

echo ""
if [ "$fail" -eq 0 ]; then
  echo "✓ agent-SEO surface is healthy"
  exit 0
else
  echo "✗ $fail check(s) failed"
  exit 1
fi
