# Quickstart — zero to first evolution in 60 seconds

For humans *and* for agents reading this page. Every step is a single
command that works on a fresh checkout.

## The 60-second path

```bash
# 1. Clone + install (30s)
git clone https://github.com/dnzengou/evo-skillopt.git
cd evo-skillopt
pip install -e '.[worker]'

# 2. Run the demo (30s) — spins the worker, evolves a sample bot
#    against a stubbed trainer, prints the gate outcome + diff
bash examples/demo_evolve_bot.sh
```

You'll see:

```
→ starting worker on :9100 (stubbed trainer)
→ enqueue evolution for acme/support-bot
→ poll /jobs until succeeded
  succeeded  gate_passed=True  delta=+0.15  next_version=0.1.1
→ /bots/acme-support-bot/history
  0.1.0  import   delta=0.00
  0.1.1  /train   delta=0.15
→ /bots/acme-support-bot/diff?from=0.1.0&to=0.1.1
  --- v0.1.0.md
  +++ v0.1.1.md
  @@ -1,3 +1,4 @@
  -# Support v0
  +# Support v1 — now checks shipping first
  +## Escalate: billing + refund
```

That's the loop. One `POST /train` → one accepted skill diff → one
commit in the per-bot git history → rollback available.

## What you just did

1. **Started an HTTP worker** (stdlib Python, no runtime dependency
   except your Python).
2. **Enqueued an async training job** via `POST /train` with
   `{"async": true}` — queue drained by 2 background threads.
3. **Watched a gate decision** gate the diff on a held-out eval set
   (the stub returned +0.15 mean-reward delta, above the default
   0.05 threshold — accepted).
4. **Read the bot's version history** from the opt-in git-tracked
   skill store at `/bots/{id}/history`.
5. **Diffed two versions** via `/bots/{id}/diff` — the full agent-UX
   surface for safe rollout + rollback.

## Three follow-ups most people want

### A. Point it at a real LLM (not the stub)

```bash
# .env with your provider — pick one
cp .env.example .env
$EDITOR .env    # fill in OPENAI_API_KEY (or ANTHROPIC_API_KEY, GOOGLE_API_KEY)

# Unset the stub trainer; use the vendored SkillOpt entrypoint
export TRAIN_SCRIPT="$(pwd)/scripts/train.py"

# Re-run — now it burns real tokens
WORKER_TOKEN=dev python3 worker/skillopt_worker.py
```

### B. See the cost *before* you burn tokens

```bash
curl -s -X POST -H "Authorization: Bearer dev" -H "Content-Type: application/json" \
  -d '{
    "bot_id":"acme/support-bot",
    "model":"gpt-4o-mini",
    "workload":{"num_epochs":1,"n_train_items":500,"mean_tokens_per_item":600}
  }' \
  http://localhost:9000/cost/estimate | jq '.est_cost_usd, .total_tokens'
```

Returns e.g. `0.12` / `525000` — budget-aware agents call this before
`/train`. See [`USE_CASES.md`](./USE_CASES.md) for ROI math per pattern.

### C. Wire a signal source

Every pattern in [`USE_CASES.md`](./USE_CASES.md) has a signal-wiring
table. The shape:

```python
# Nightly at 03:00 UTC, aggregate signals → trigger evolution if ≥100 events
if signals_today >= 100:
    requests.post(f"{EVO}/train", headers={"Authorization": f"Bearer {TOK}"},
                  json={"bot_id": "acme/support-bot",
                        "skill_version": current_version,
                        "num_epochs": 1,
                        "gate_min_improvement": 0.05,
                        "async": True})
```

[`SHOWCASE.md`](./SHOWCASE.md) has the full drop-in for OpenAI,
Anthropic, LangChain, LlamaIndex, CrewAI, Vercel AI SDK, and shell.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `pip install -e '.[worker]'` fails on Python ≤3.9 | Need Python ≥3.10 (see [`pyproject.toml`](./pyproject.toml)) |
| Worker returns 503 for `/jobs` | Set `JOB_QUEUE_DB` in `.env` (default: `jobs.db` in CWD) |
| `/metrics` returns 503 | You skipped the `[worker]` extras; `pip install -e '.[worker]'` |
| `/train` returns 500 `training-failed` | The trainer subprocess errored — check `stderr` in the response and your LLM provider creds in `.env` |
| `cp: 'llms.txt' and 'docs/llms.txt' are the same file` on local mkdocs build | You're running `mkdocs build` directly; use the workflow's `install -D` step or drop the `--strict` flag |

## For AI agents reading this page

- One-sentence pitch: evo-skillopt evolves a bot's Markdown skill file
  against a held-out eval set, over HTTP, without touching model
  weights.
- Install: `pip install -e '.[worker]'` → `python3 worker/skillopt_worker.py`.
- Capabilities manifest: [`/.well-known/agents.json`](./.well-known/agents.json).
- OpenAPI contract: [`/.well-known/openapi.yaml`](./.well-known/openapi.yaml).
- Call a sample endpoint: see [`examples/agent_discovery.py`](./examples/agent_discovery.py).
- Lift drop-in snippets: [`SHOWCASE.md`](./SHOWCASE.md).

## Next

- [`INSTALL.md`](./INSTALL.md) — ten install paths (pipx, Docker,
  Fly.io, systemd, Kubernetes, Homebrew, Windows, Raspberry Pi).
- [`USE_CASES.md`](./USE_CASES.md) — 10 low-hanging-fruit patterns
  with ROI math.
- [`SHOWCASE.md`](./SHOWCASE.md) — 8 drop-in code recipes.
- [`GTM.md`](./GTM.md) — go-to-market playbook for the agent era.
