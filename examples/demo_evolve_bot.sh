#!/usr/bin/env bash
# demo_evolve_bot.sh — "aha moment" in one command.
#
# Spins a worker with a stubbed trainer, enqueues one evolution for a
# sample bot, polls until the job succeeds, prints the history, and
# shows the diff between the two versions.
#
# Target wall-clock: < 20 seconds end-to-end.
#
# Usage:
#   bash examples/demo_evolve_bot.sh                     # defaults below
#   PORT=9211 bash examples/demo_evolve_bot.sh           # custom port
#
# No external dependencies beyond `python3`, `curl`, and `jq`.

set -u

HERE=$(cd "$(dirname "$0")/.." && pwd)
PORT=${PORT:-9200}
URL="http://127.0.0.1:${PORT}"
TOKEN="demo-token"
BOT="acme/support-bot"
SLUG="acme-support-bot"

# Everything the demo touches lives in a fresh tmp dir — we clean up
# on exit, so the repo state is unchanged after the run.
TMP=$(mktemp -d -t evo-demo-XXXXXX)
STORE="$TMP/bots"
OUT="$TMP/outputs"
QDB="$TMP/jobs.db"
STUB="$TMP/fake_train.py"
LOG="$TMP/worker.log"

cleanup() {
  local code=$?
  if [ -n "${WORKER_PID:-}" ] && kill -0 "$WORKER_PID" 2>/dev/null; then
    kill -TERM "$WORKER_PID" 2>/dev/null
    wait "$WORKER_PID" 2>/dev/null
  fi
  rm -rf "$TMP"
  exit $code
}
trap cleanup EXIT INT TERM

step() { printf "\n\033[1;36m→ %s\033[0m\n" "$*"; }
fail() { printf "\n\033[1;31m✗ %s\033[0m\n" "$*" >&2; exit 1; }
pretty_json() {
  if command -v jq >/dev/null 2>&1; then jq .
  else python3 -m json.tool
  fi
}

command -v curl >/dev/null || fail "curl is required"
command -v python3 >/dev/null || fail "python3 is required"

# ─── 1. Stub the SkillOpt trainer ────────────────────────────────────
cat > "$STUB" <<'PYEOF'
"""Minimal stub trainer: write a history.json showing +0.15 mean-reward
delta and emit the evolved skill. Used only by demo_evolve_bot.sh."""
import json, pathlib, sys
args = sys.argv
try:
    out = args[args.index("--out_root") + 1]
except (ValueError, IndexError):
    sys.exit(2)
p = pathlib.Path(out); p.mkdir(parents=True, exist_ok=True)
(p / "history.json").write_text(json.dumps({
    "steps": [{"val_reward": 0.80}, {"val_reward": 0.95}],
}))
(p / "skill.md").write_text(
    "# Support v1 — now checks shipping first\n"
    "## Escalate: billing + refund\n"
    "- Match the customer's tone one level warmer.\n"
    "- Never fabricate a policy.\n"
)
sys.exit(0)
PYEOF

# ─── 2. Seed the skill store with v0.1.0 so there's history to show ──
mkdir -p "$STORE"
python3 - <<PYEOF
import os, sys
sys.path.insert(0, "$HERE/worker")
os.environ["SKILL_STORE_ROOT"] = "$STORE"
os.environ["SKILL_STORE_USE_GIT"] = "0"
import skill_store
skill_store.SKILL_STORE_ROOT = __import__("pathlib").Path("$STORE").resolve()
skill_store.SKILL_STORE_USE_GIT = False
skill_store.put_version(
    "$BOT", "0.1.0",
    "# Support v0\n## Escalate: billing + refund\n- Keep it short.\n",
    source="import", note="seed",
)
print("seeded v0.1.0 for $BOT")
PYEOF

# ─── 3. Start the worker ─────────────────────────────────────────────
step "starting worker on :$PORT (stubbed trainer, tmp store at $TMP)"
WORKER_TOKEN="$TOKEN" PORT="$PORT" \
  JOB_QUEUE_DB="$QDB" JOB_QUEUE_WORKERS=1 \
  SKILL_STORE_ROOT="$STORE" SKILL_STORE_USE_GIT=0 \
  TRAIN_SCRIPT="$STUB" OUTPUT_ROOT="$OUT" \
  LOG_LEVEL=WARNING \
  python3 "$HERE/worker/skillopt_worker.py" > "$LOG" 2>&1 &
WORKER_PID=$!

# Wait for /health to return 200
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sf "$URL/health" > /dev/null 2>&1; then break; fi
  sleep 0.4
done
if ! curl -sf "$URL/health" > /dev/null 2>&1; then
  fail "worker never came up — see $LOG"
fi

# ─── 4. Enqueue evolution ────────────────────────────────────────────
step "enqueue evolution for $BOT"
JOB_ID=$(curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"bot_id\":\"$BOT\",\"skill_version\":\"0.1.0\",\"num_epochs\":1,\"async\":true}" \
  "$URL/train" | python3 -c "import json,sys;print(json.load(sys.stdin)['job_id'])")
echo "  job_id: $JOB_ID"

# ─── 5. Poll until the job is terminal ───────────────────────────────
step "poll /jobs until succeeded"
STATUS=queued
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  STATUS=$(curl -s -H "Authorization: Bearer $TOKEN" "$URL/jobs/$JOB_ID" \
           | python3 -c "import json,sys;print(json.load(sys.stdin)['job']['status'])")
  case "$STATUS" in
    succeeded|failed|timeout) break ;;
  esac
  sleep 0.5
done
RESP=$(curl -s -H "Authorization: Bearer $TOKEN" "$URL/jobs/$JOB_ID")
echo "$RESP" | python3 -c "
import json,sys
j=json.load(sys.stdin)['job']
r=j.get('result') or {}
print(f\"  {j['status']}  gate_passed={r.get('gate_passed')}  \"
      f\"delta=+{r.get('gate_score_delta')}  next_version={r.get('next_version')}\")
"

if [ "$STATUS" != "succeeded" ]; then
  fail "job did not succeed; response was:\n$(echo "$RESP" | pretty_json)"
fi

# ─── 6. Record the accepted skill as v0.1.1 so /history + /diff work ─
step "persisting accepted skill as v0.1.1"
python3 - <<PYEOF
import os, pathlib, sys
sys.path.insert(0, "$HERE/worker")
os.environ["SKILL_STORE_ROOT"] = "$STORE"
import skill_store
skill_store.SKILL_STORE_ROOT = pathlib.Path("$STORE").resolve()
skill_store.SKILL_STORE_USE_GIT = False
# Find the latest run output dir and pull its skill.md
import json
latest = sorted(pathlib.Path("$OUT").glob("$SLUG-v*"))[-1]
content = (latest / "skill.md").read_text()
skill_store.put_version("$BOT", "0.1.1", content,
                        gate_score_delta=0.15, source="/train")
print("  stored v0.1.1 (gate delta +0.15)")
PYEOF

# ─── 7. Read history + diff ──────────────────────────────────────────
step "/bots/$SLUG/history"
curl -s -H "Authorization: Bearer $TOKEN" "$URL/bots/$SLUG/history" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
for v in d['versions']:
    print(f\"  {v['version']}  {v['source']:>8}  delta={v.get('gate_score_delta', 0.0)}\")
"

step "/bots/$SLUG/diff?from=0.1.0&to=0.1.1"
curl -s -H "Authorization: Bearer $TOKEN" \
  "$URL/bots/$SLUG/diff?from=0.1.0&to=0.1.1" | sed 's/^/  /'

printf "\n\033[1;32m✓ demo complete\033[0m — one evolution, gated, versioned, diffable.\n"
printf "\nNext steps are in \033[4mQUICKSTART.md\033[0m.\n"
