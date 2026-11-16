#!/usr/bin/env bash
# agent-seo-kit scaffold — drop the agent-SEO surface into any project.
#
# Usage:
#   cd /path/to/target/project
#   PROJECT_NAME="my-project" \
#   PROJECT_OWNER="myuser" \
#   PROJECT_REPO="my-project" \
#   PROJECT_DESCRIPTION="One-sentence pitch." \
#     bash /path/to/evo-skillopt/tools/agent-seo-kit/scaffold.sh
#
# Or with --flags:
#   scaffold.sh --name my-project --owner myuser --repo my-project \
#               --description "One-sentence pitch."
#
# The scaffold:
#   - Copies templates with placeholder substitution.
#   - Refuses to overwrite existing files (use --force to override).
#   - Writes a project-local verify.sh.
#   - Prints a 5-line post-install checklist.

set -u

NAME=${PROJECT_NAME:-}
OWNER=${PROJECT_OWNER:-}
REPO=${PROJECT_REPO:-}
DESCRIPTION=${PROJECT_DESCRIPTION:-""}
TARGET=${PROJECT_TARGET:-$(pwd)}
FORCE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --name)        NAME=$2; shift 2 ;;
    --owner)       OWNER=$2; shift 2 ;;
    --repo)        REPO=$2; shift 2 ;;
    --description) DESCRIPTION=$2; shift 2 ;;
    --target)      TARGET=$2; shift 2 ;;
    --force)       FORCE=1; shift ;;
    -h|--help)     head -22 "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

[ -z "$NAME" ]  && { echo "--name (or PROJECT_NAME) is required" >&2; exit 2; }
[ -z "$OWNER" ] && { echo "--owner (or PROJECT_OWNER) is required" >&2; exit 2; }
[ -z "$REPO" ]  && { echo "--repo (or PROJECT_REPO) is required" >&2; exit 2; }

HERE=$(cd "$(dirname "$0")" && pwd)
TEMPLATES="$HERE/templates"

if [ ! -d "$TEMPLATES" ]; then
  echo "templates dir not found at $TEMPLATES" >&2; exit 1
fi

info() { printf "  %s\n" "$*"; }
ok()   { printf "  \033[32m✓\033[0m %s\n" "$*"; }
skip() { printf "  \033[33m↷\033[0m %s (already exists; --force to override)\n" "$*"; }

render() {
  # Expand {{placeholders}} without needing jinja/sed-fu edge cases.
  local src=$1 dst=$2
  if [ -e "$dst" ] && [ "$FORCE" -ne 1 ]; then
    skip "$(realpath --relative-to="$TARGET" "$dst")"
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  # Env vars must be set BEFORE the python command (shell rule); KEY=val
  # tokens after `python3 ...` become argv, not env.
  NAME="$NAME" OWNER="$OWNER" REPO="$REPO" DESCRIPTION="$DESCRIPTION" \
    SRC="$src" DST="$dst" \
    python3 -c '
import os
src=os.environ["SRC"]; dst=os.environ["DST"]
content=open(src).read()
for k, v in {
    "project":    os.environ["NAME"],
    "owner":      os.environ["OWNER"],
    "repo":       os.environ["REPO"],
    "description":os.environ["DESCRIPTION"] or (os.environ["NAME"] + " — <one-sentence pitch>"),
}.items():
    content = content.replace("{{" + k + "}}", v)
open(dst, "w").write(content)
'
  ok "$(realpath --relative-to="$TARGET" "$dst")"
}

printf "scaffolding agent-SEO surface for %s/%s (%s)\n\n" "$OWNER" "$REPO" "$NAME"

render "$TEMPLATES/AGENTS.md"               "$TARGET/AGENTS.md"
render "$TEMPLATES/llms.txt"                "$TARGET/llms.txt"
render "$TEMPLATES/llms-full.txt"           "$TARGET/llms-full.txt"
render "$TEMPLATES/robots.txt"              "$TARGET/robots.txt"
render "$TEMPLATES/CITATION.cff"            "$TARGET/CITATION.cff"
render "$TEMPLATES/.well-known/agents.json" "$TARGET/.well-known/agents.json"
render "$TEMPLATES/.well-known/openapi.yaml" "$TARGET/.well-known/openapi.yaml"
render "$TEMPLATES/README-jsonld.html"      "$TARGET/.agent-seo/README-jsonld.html"
render "$TEMPLATES/verify.sh"               "$TARGET/.agent-seo-verify.sh"
chmod +x "$TARGET/.agent-seo-verify.sh" 2>/dev/null

cat <<EOF

Done. 5-line checklist to finish:
  1. Open AGENTS.md — fill in your repo's layout, "where the code is" table, and testing commands.
  2. Open llms.txt + llms-full.txt — replace the <one-sentence pitch> placeholders.
  3. Open .well-known/agents.json — list your real endpoints + their auth model.
  4. Open .well-known/openapi.yaml — paste your real OpenAPI paths (or point it at your real spec).
  5. Paste the JSON-LD from .agent-seo/README-jsonld.html into your README.md inside <script type="application/ld+json">...</script> tags.

Verify locally:
  bash .agent-seo-verify.sh

Verify a live site:
  SITE=https://${OWNER}.github.io/${REPO} bash .agent-seo-verify.sh
EOF
