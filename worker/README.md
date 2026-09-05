# evo-skillopt worker

Stdlib-only Python HTTP service. Wraps SkillOpt's `scripts/train.py` and
exposes text-space skill optimization as a callable HTTP API.

## Endpoints

| Method | Path              | Purpose                                                             |
|--------|-------------------|---------------------------------------------------------------------|
| GET    | `/health`         | Liveness probe (unauthenticated)                                    |
| POST   | `/train`          | Run one training pass (bearer auth if `WORKER_TOKEN` is set)        |
| POST   | `/train/cascade`  | Aggregate + gate a cascade of per-stage scores (no training)        |
| POST   | `/fitness/arm`    | Reduce ARM-bucketed signals to one composite fitness (no training)  |

## Environment

| Var             | Default             | Purpose                                       |
|-----------------|---------------------|-----------------------------------------------|
| `WORKER_TOKEN`  | *(unset — dev)*     | Bearer token required on `POST /train`        |
| `OUTPUT_ROOT`   | `outputs/evo`       | Where training runs write outputs             |
| `TRAIN_SCRIPT`  | `scripts/train.py`  | Path to SkillOpt's train entrypoint           |
| `PORT`          | `9000`              | Listen port                                   |

Additional environment variables — API keys for whichever LLM backend
SkillOpt is configured to call — are documented in `../.env.example`.

## Local dev

```bash
WORKER_TOKEN=dev-token python3 skillopt_worker.py
curl http://localhost:9000/health
```

## Docker Compose (self-host)

```bash
cp ../.env.example ../.env    # fill in your API keys
docker compose --env-file ../.env up --build -d
curl http://localhost:9000/health
```

## Fly.io deploy

```bash
# One-time
curl -L https://fly.io/install.sh | sh
fly auth login

fly apps create evo-skillopt-worker           # or pick a unique name
fly volumes create evo_data --region ord --size 1
fly secrets set WORKER_TOKEN="$(openssl rand -hex 32)"

# Provider secrets — set whichever backend you use
fly secrets set OPENAI_API_KEY=sk-...
# fly secrets set ANTHROPIC_API_KEY=sk-ant-...
# fly secrets set GOOGLE_API_KEY=...

fly deploy

curl https://<your-app>.fly.dev/health
```

## Calling the training endpoint

```bash
curl -X POST https://<your-app>.fly.dev/train \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bot_id":               "acme/support-bot",
    "skill_version":        "0.1.0",
    "skill_path":           "/data/bots/acme-support-bot/skills/main.md",
    "eval_split_dir":       "/data/bots/acme-support-bot/eval",
    "config":               "configs/searchqa/default.yaml",
    "num_epochs":           1,
    "gate_min_improvement": 0.05
  }'
```

Response schema:

```json
{
  "ok":                true,
  "gate_passed":       true,
  "gate_score_delta":  0.073,
  "next_version":      "0.1.1",
  "output_dir":        "outputs/evo/acme-support-bot-v0.1.1-<ts>",
  "duration_s":        412,
  "job_id":            "<uuid>"
}
```

## RRSS gate (optional overlay)

Add an `rrss` block to the `/train` payload to score the candidate across
four resilience axes — Robustify, Reliabilify, Solidify, Stabilize — and
gate on the composite. See
[`../configs/examples/rrss_gate.yaml`](../configs/examples/rrss_gate.yaml)
for the payload shape and
[`rrss_gate.py`](./rrss_gate.py) for the axis definitions.

When present, the RRSS composite replaces the base `gate_score_delta` in
the accept/reject decision; the base delta is still returned in the
response, alongside the four axis scores and the pass/reject reason.

## Cascade endpoint

`POST /train/cascade` aggregates and gates a *pipeline* of already-scored
skills — e.g. `[filter_pii, classify_intent, draft_reply]` — into one
pass/fail. It performs no training; call it after producing per-stage
scores (from prior `/train` runs, offline evals, or CI harnesses).

```bash
curl -X POST https://<your-app>.fly.dev/train/cascade \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bot_id": "acme/support-bot",
    "stages": [
      {"name": "filter",   "score": 0.94},
      {"name": "classify", "score": 0.88},
      {"name": "draft",    "score": 0.91, "weight": 2.0}
    ],
    "aggregation":         "weighted_mean",
    "aggregate_threshold": 0.85,
    "stage_floor":         0.60
  }'
```

Response:

```json
{
  "ok":           true,
  "gate_passed":  true,
  "aggregate":    0.9100,
  "aggregation":  "weighted_mean",
  "reason":       "aggregate 0.910 ≥ 0.850 (weighted_mean)",
  "stages": [
    {"name": "filter",   "score": 0.94, "weight": 1.0},
    {"name": "classify", "score": 0.88, "weight": 1.0},
    {"name": "draft",    "score": 0.91, "weight": 2.0}
  ],
  "job_id": "<uuid>"
}
```

### Auto-deriving RRSS inputs

The RRSS overlay accepts inputs inline (as shown above) *or* it can
derive them from the run's own outputs. Set `rrss.auto_from_history:
true` and the worker reads:

* `<output_dir>/rollouts/current.jsonl` — one row per eval item:
  `{"score": 0.83, "category": "billing"}`.
* `<output_dir>/history.json` — the trainer's per-epoch summary
  (`steps[*].val_reward` seeds Reliabilify).
* an optional `rrss.prev_rollouts_path` — same shape as
  `current.jsonl` for the previously-accepted skill (seeds Stabilize).

See [`rrss_from_history.py`](./rrss_from_history.py) for the exact
conventions and defaults.

## ARM fitness endpoint

`POST /fitness/arm` reduces a batch of production signals to one
composite fitness score, bucketed by lifecycle stage (Acquire, Retain,
Monetize). Pure aggregation — no training. Meant to be called by
whatever collects your bot's production signals so they can hand the
worker a single number to gate evolutions on.

```bash
curl -X POST https://<your-app>.fly.dev/fitness/arm \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bot_id": "acme/support-bot",
    "signals": [
      {"bucket": "acquire",  "delta": 1.0, "kind": "trial_started"},
      {"bucket": "retain",   "delta": 0.5, "kind": "csat_5"},
      {"bucket": "monetize", "delta": 2.0, "kind": "plan_upgrade"}
    ],
    "weights": {"acquire": 0.3, "retain": 0.5, "monetize": 0.2}
  }'
```

Response:

```json
{
  "ok":        true,
  "composite": 0.95,
  "weights":   {"acquire": 0.3, "retain": 0.5, "monetize": 0.2},
  "per_bucket": [
    {"bucket": "acquire",  "count": 1, "sum_delta": 1.0, "mean_delta": 1.0},
    {"bucket": "retain",   "count": 1, "sum_delta": 0.5, "mean_delta": 0.5},
    {"bucket": "monetize", "count": 1, "sum_delta": 2.0, "mean_delta": 2.0}
  ],
  "job_id": "<uuid>"
}
```

Rebalance `weights` over the product lifecycle:

| Stage   | acquire | retain | monetize |
|---------|--------:|-------:|---------:|
| launch  |    0.60 |   0.30 |     0.10 |
| growth  |    0.30 |   0.50 |     0.20 |
| mature  |    0.10 |   0.40 |     0.50 |

See [`../EvoSkillOpt_Blueprint.md`](../EvoSkillOpt_Blueprint.md) for the
full picture — capabilities, roadmap, and use-case catalog.
