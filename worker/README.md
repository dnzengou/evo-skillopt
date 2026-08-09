# evo-skillopt worker

Stdlib-only Python HTTP service. Wraps SkillOpt's `scripts/train.py` and
exposes text-space skill optimization as a callable HTTP API.

## Endpoints

| Method | Path       | Purpose                                                      |
|--------|------------|--------------------------------------------------------------|
| GET    | `/health`  | Liveness probe (unauthenticated)                             |
| POST   | `/train`   | Run one training pass (bearer auth if `WORKER_TOKEN` is set) |

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

See [`../EvoSkillOpt_Blueprint.md`](../EvoSkillOpt_Blueprint.md) for the
full picture — capabilities, roadmap, and use-case catalog.
