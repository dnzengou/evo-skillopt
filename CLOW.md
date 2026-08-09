# Clow — Manual & Reference
## v1.0 · Aug 2026

> The agent economy for PicoClaw bots. Deploy on $10 hardware. Bots evolve through use.

**Live:** [clow-tau.vercel.app](https://clow-tau.vercel.app) · **Repo:** [github.com/dnzengou/clow](https://github.com/dnzengou/clow) · **Backend & GTM:** this branch (`claude/clow-bots-marketing-gtm-p6nTm` on `dnzengou/SkillOpt`)

---

## Table of contents

1. [What is Clow](#1-what-is-clow)
2. [Architecture](#2-architecture)
3. [Repo layout](#3-repo-layout)
4. [Prerequisites](#4-prerequisites)
5. [Installation (local dev)](#5-installation-local-dev)
6. [Deployment (production)](#6-deployment-production)
7. [Usage — the bot lifecycle](#7-usage--the-bot-lifecycle)
8. [Applications — the 3 sample bots](#8-applications--the-3-sample-bots)
9. [Examples — real request/response flows](#9-examples--real-requestresponse-flows)
10. [API reference](#10-api-reference)
11. [Contributing](#11-contributing)
12. [Troubleshooting](#12-troubleshooting)
13. [Links](#13-links)

---

## 1. What is Clow

Three sentences:

**Clow is the marketplace layer for PicoClaw bots** — where users discover, deploy, and pay for AI bots that run on their own hardware (down to a $10 RISC-V board) or a $5 VPS.

**The differentiator: bots on Clow evolve.** Every conversation is a training step; every weekly epoch produces a smarter skill document, gated by a held-out eval set. Uses [SkillOpt](https://arxiv.org/abs/2605.23904) (arXiv:2605.23904) — text-space optimization without touching model weights.

**Two flywheels reinforce each other:** supply-side (publishers earn 70% of marketplace revenue, EvoMetaClaw improves their bot for free) and demand-side (users get better bots + a "Certified Secure" trust badge from continuous scanning).

**Where it sits in the Claw ecosystem:** OpenClaw (215k+ stars, personal AI assistant) and its cousins (MaxClaw, KimiClaw, ZeroClaw, PicoClaw, EnterpriseClaw) are *agents*. Clow is the *marketplace* where their bots live and evolve. Different layer of the stack.

---

## 2. Architecture

```
                             ┌────────────────────────┐
                             │   clow_landing.html    │
                             │ (Vercel · static + edge)│
                             └───────────┬────────────┘
                                         │ POST /api/waitlist
                                         │ POST /api/og (dynamic OG)
                                         ▼
              ┌──────────────────────────────────────────────────┐
              │  Vercel Edge Functions (api/*.js)                │
              │  • waitlist.js → tries gtm-engine → gh-issues    │
              │  • og.js       → dynamic 1200×630 PNG            │
              └──────────────────┬───────────────────────────────┘
                                 │ bearer-auth
                                 ▼
      ┌──────────────────────────────────────────────────────────┐
      │  Fly.io backend (clow-agents/backend/)                   │
      │                                                          │
      │  ┌───────────────┐ ┌────────────────┐ ┌──────────────┐  │
      │  │  gtm-engine   │ │ security-agent │ │ evo-metaclaw │  │
      │  │  ICP + deals  │ │  scans + badge │ │ fitness + evo│  │
      │  └───────┬───────┘ └────────┬───────┘ └──────┬───────┘  │
      │          │                  │                │           │
      │          └──────────────────┴────────────────┘           │
      │                        │                                 │
      │                        ▼                                 │
      │              KafCa (shared bus)                          │
      │            ┌───────────────────┐                         │
      │            │ • events (broadcast)                         │
      │            │ • trajectory_signals                         │
      │            │ • audit_logs                                 │
      │            │ • SQLite per service                         │
      │            └───────────────────┘                         │
      └───────────────────┬──────────────────────────────────────┘
                          │ SKILLOPT_WORKER_URL (optional)
                          ▼
              ┌──────────────────────────┐
              │  scripts/skillopt_worker │
              │  Python · POST /train    │
              │  → scripts/train.py      │
              │  → real SkillOpt loop    │
              └──────────────────────────┘

                    ▲  RRSS wraps all layers  ▲
                    Robustify · Reliabilify · Solidify · Stabilize
```

Full name-space glossary: [EvoStack.md](./EvoStack.md).

---

## 3. Repo layout

```
SkillOpt/                        (this fork of Microsoft/SkillOpt)
├── README.md                    # SkillOpt's own README (unchanged)
├── CLOW.md                      # THIS FILE — Clow manual
├── CLAUDE.md                    # devflow project context
├── EvoStack.md                  # name-space cheat sheet
├── EvoMetaClaw.md               # self-evolving bots concept + arch
├── MARKETING.md                 # full ARM GTM strategy (8 phases)
├── Clow_GTM_Blueprint.md        # living roadmap w/ changelog
├── DEPLOY.md                    # deployment checklist
├── X_THREADS.md                 # copy-paste X threads for @XTech73781
├── clow_bot_template.md         # bot publisher onramp
│
├── clow_landing.html            # production landing (Vercel: /)
├── use_cases.html               # 3-bot showcase (Vercel: /use-cases)
├── dashboard.html               # ops dashboard (Vercel: /dashboard)
│
├── api/                         # Vercel Edge Functions
│   ├── waitlist.js              # POST → gtm-engine → gh-issues fallback
│   └── og.js                    # dynamic OG image (@vercel/og)
├── vercel.json                  # routes + CSP/HSTS headers
├── .env.vercel.example          # Vercel env template
│
├── bots/                        # marketplace-at-launch inventory
│   ├── telegram-summarizer/     # free tier
│   ├── discord-moderator/       # $3/mo
│   └── slack-standup/           # $5/mo
│
├── scripts/                     # ops
│   ├── deploy_fullstack.sh      # 1-cmd Fly + Vercel deploy
│   ├── deploy_vercel.sh         # 1-cmd Vercel only
│   ├── smoke.sh                 # health probe of all 4 services
│   └── skillopt_worker.py       # stdlib HTTP bridge → train.py
│
├── clow-agents/backend/         # Rust workspace (Axum, SQLite, KafCa bus)
│   ├── Cargo.toml               # workspace manifest
│   ├── Cargo.lock               # committed for reproducible Fly builds
│   ├── shared/                  # KafCa bus, auth, db, models, notify
│   ├── gtm-engine/              # ICP scoring, deal pipeline, MRR forecast
│   ├── security-agent/          # scans → Certified Secure badge
│   └── evo-metaclaw/            # trajectory ingest, fitness, evolution
│
└── .github/workflows/ci.yml     # cargo check + node check + py compile
```

---

## 4. Prerequisites

Install what you need for the parts you plan to run.

| Tool | Version | Where used |
|------|---------|------------|
| `git` | any | everything |
| `node` | ≥ 20 | Vercel deploy (`vercel` CLI) |
| `npm` | any | `npm i @vercel/og` for OG endpoint |
| `python3` | ≥ 3.9 | `scripts/skillopt_worker.py` + SkillOpt itself |
| `rust` / `cargo` | ≥ 1.78 stable | building `clow-agents/backend/` locally |
| `vercel` CLI | latest | `npm i -g vercel` for landing deploy |
| `flyctl` | latest | `curl -L https://fly.io/install.sh \| sh` for backend deploy |
| `curl` + `jq` | any | testing endpoints |

**Accounts** you'll need:
- **GitHub** (already have) — for the repo + optional waitlist fallback via Issues
- **Vercel** — free tier is plenty for the landing
- **Fly.io** — free tier covers 3 small services (auto-stop when idle)
- **Slack incoming webhook** (optional) — for hot-lead + evolution alerts

---

## 5. Installation (local dev)

### 5.1. Get the code

```bash
git clone https://github.com/dnzengou/SkillOpt.git
cd SkillOpt
git checkout claude/clow-bots-marketing-gtm-p6nTm
```

### 5.2. Landing (browser-only, zero setup)

```bash
open clow_landing.html          # macOS
xdg-open clow_landing.html      # Linux
# Waitlist form works but POSTs to /api/waitlist which isn't served.
# Landing-side localStorage fallback catches the email either way.
```

### 5.3. Rust backend (`clow-agents/backend/`)

```bash
cd clow-agents/backend
cargo build                     # first build takes ~5 min
cargo check --workspace         # sanity
```

Run one service:

```bash
API_TOKEN="dev-token" \
DATABASE_URL="sqlite:///tmp/gtm.db?mode=rwc" \
PORT=18080 \
RUST_LOG=info \
cargo run -p gtm-engine
```

Repeat for `security-agent` (port 18081) and `evo-metaclaw` (port 18082) in separate shells.

### 5.4. SkillOpt Python worker

```bash
# From repo root (Python worker uses SkillOpt's existing scripts/train.py)
pip install -e .
WORKER_TOKEN="dev-worker-token" PORT=9000 python3 scripts/skillopt_worker.py
```

### 5.5. Smoke everything

```bash
GTM=http://localhost:18080 \
SEC=http://localhost:18081 \
EVO=http://localhost:18082 \
WORKER=http://localhost:9000 \
API_TOKEN=dev-token \
./scripts/smoke.sh
```

You should see 8 `✓` lines and an `✓ all green` at the bottom.

---

## 6. Deployment (production)

### 6.1. One-command full stack (recommended)

```bash
# One-time
curl -L https://fly.io/install.sh | sh   # flyctl
npm i -g vercel                           # vercel CLI
fly auth login  &&  vercel login  &&  vercel link

# Every deploy — Fly backend (3 services) + Vercel landing, sequenced
export API_TOKEN=$(openssl rand -hex 32)             # shared bearer
export SLACK_WEBHOOK=https://hooks.slack.com/...     # optional
PREFIX=ds- ./scripts/deploy_fullstack.sh
```

`PREFIX=ds-` prepends to Fly app names (Fly names are globally unique — the defaults are taken). Script auto-creates apps + volumes + secrets, wires `GTM_ENGINE_URL`/`_TOKEN` on Vercel, then runs `smoke.sh`.

### 6.2. Landing only (skip Fly backend)

Waitlist falls back to **GitHub Issues** — zero third-party SaaS.

```bash
# Create private repo (any name); create fine-grained PAT with issues:write
vercel env add GH_TOKEN production      # paste github_pat_...
vercel env add GH_REPO  production      # type: your-name/clow-waitlist
./scripts/deploy_vercel.sh
```

Every signup becomes one labeled GitHub issue (`waitlist`, `source:...`, `plan:...`). Filter via GitHub's own issue search.

### 6.3. Backend only

```bash
SKIP_VERCEL=1 API_TOKEN=... ./scripts/deploy_fullstack.sh
```

### 6.4. SkillOpt worker (optional but recommended for real evolution)

The Rust `evo-metaclaw` simulates gate outcomes by default. To use the real SkillOpt training loop, run the worker somewhere reachable by evo-metaclaw (Fly VM, personal server, or same Fly org):

```bash
# On the worker host
export WORKER_TOKEN=$(openssl rand -hex 32)
export OUTPUT_ROOT=/data/evo-outputs
PORT=9000 python3 scripts/skillopt_worker.py

# Then tell evo-metaclaw about it
fly secrets set -a ds-evo-metaclaw \
  SKILLOPT_WORKER_URL=http://<worker-host>:9000 \
  SKILLOPT_WORKER_TOKEN=<same as WORKER_TOKEN>
```

Full details: [DEPLOY.md](./DEPLOY.md).

---

## 7. Usage — the bot lifecycle

### 7.1. As a bot user (consumer)

1. Visit `/use-cases`, pick a bot
2. Click "Get access" → join waitlist (email captured)
3. When accepted: get a Clow account + generate a bot token for your channel (Telegram/Discord/Slack)
4. Paste `clow deploy <bot-slug> --channel telegram --token $TG_TOKEN` (or use the web dashboard)
5. Bot runs on your $10 board or a $5 VPS
6. Weekly: EvoMetaClaw ships a skill update (if Pro tier) — email digest tells you what changed

### 7.2. As a bot publisher (supplier)

1. Fork `clow_bot_template.md` or one of the bots in `bots/`
2. Edit `clow_bot.yaml` — name, tier (free / $X / $X mo), channels, LLM config
3. Write `skills/main.md` — the skill document (500–800 lines sweet spot)
4. Write `eval/held_out.json` — 20+ test cases with reward_criteria
5. `clow publish` — validates + uploads to the marketplace
6. When bots get ≥ 100 conversations, EvoMetaClaw takes over the iteration loop
7. Every accepted evolution earns you 70% of any paid conversions triggered by improved reviews

### 7.3. As an operator (running the stack)

1. Deploy per section 6
2. Watch **dashboard.html** (Vercel: `/dashboard`) — MRR forecast, top leads, evolution leaderboard, security findings
3. Weekly: publish an X thread from `X_THREADS.md` via `@XTech73781` — the "Bot of the Week" is auto-generatable from `/leaderboard`
4. Monthly: review `Clow_GTM_Blueprint.md` ARM scores; update the changelog

---

## 8. Applications — the 3 sample bots

Each ships in `bots/<name>/` with `clow_bot.yaml` + `skills/main.md` + `eval/held_out.json`.

### 8.1. `telegram-summarizer` (Free)

**What:** Digests noisy Telegram group chats into hourly / daily summaries. Names topics, cites message counts (never verbatim quotes for privacy), auto-redacts secrets, extracts action items.

**Deploy:** `clow deploy clow-team/telegram-summarizer --channel telegram --token $TG_BOT_TOKEN`

**Runs on:** $10 LicheeRV · **Cost:** $0/mo · **Deploy time:** 5 min

**Skill highlights:**
- `/summary Nh` command with configurable time window
- Extracts blockers: `@name will X by Y`
- Redacts anything matching API-key/OTP patterns

### 8.2. `discord-moderator` ($3/mo)

**What:** First-line Discord moderator. Scores every message (`spam` / `scam` / `off-topic` / `harassment` / `ok`), takes proportional action, escalates cleanly. Never publicly shames — DMs warnings; public actions only for repeat offenders.

**Deploy:** `clow deploy clow-team/discord-moderator --channel discord --token $DISCORD_BOT_TOKEN`

**Runs on:** Raspberry Pi Zero · **Cost:** ~$0.20/mo · **Deploy time:** 10 min

**Skill highlights:**
- Regex first pass for known scam patterns (Nitro phish, wall-of-text, invite spam)
- LLM second pass for ambiguous cases with per-user warning history
- Weekly `#mod-log` report: total actions, top offenders, false-positive rate
- Guardrails: never ban >30-day members without human confirmation

### 8.3. `slack-standup` ($5/mo)

**What:** Async daily standups. DMs each teammate 3 questions at 9:00 local. Posts digest at 12:00 team-time. Auto-follows up on blockers next day. Escalates security-context updates to on-call by DM (never to public channel).

**Deploy:** `clow deploy clow-team/slack-standup --channel slack --workspace-token $SLACK_XOXB`

**Runs on:** $5 VPS · **Cost:** ~$5/mo · **Deploy time:** 8 min

**Skill highlights:**
- Timezone-aware cron scheduling per member
- Non-responders listed neutrally ("no update from @name") — never shamed
- Weekly Friday retro: "biggest blocker of the week"

---

## 9. Examples — real request/response flows

Verified live against `gtm-engine` running locally (`API_TOKEN=ds-test-token`).

### 9.1. Ingest a waitlist signup (creates account + scores it)

```bash
curl -s -X POST http://localhost:18080/accounts \
  -H "Authorization: Bearer ds-test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "cio@fortune500-inc.com",
    "source": "producthunt",
    "plan":   "enterprise",
    "ua":     "Mozilla/5.0 (Windows NT 10.0)"
  }'
```

Response:

```json
{
  "id":              "acc-8171c752-a8c5-4310-8722-fe17facef491",
  "email":           "cio@fortune500-inc.com",
  "domain":          "fortune500-inc.com",
  "persona":         "enterprise-edge",
  "revenue_stream":  "enterprise-subscription",
  "score":           100.0,
  "status":          "new",
  "source":          "producthunt",
  "ts":              "2026-08-09T08:36:06.751Z"
}
```

Behind the scenes: emits `gtm.account.ingested` on the KafCa bus, records a `score.accepted` trajectory signal, fires a Slack hot-lead alert (persona=`enterprise-edge` AND score ≥ 70).

### 9.2. Create + advance a deal

```bash
# Create
curl -X POST http://localhost:18080/deals \
  -H "Authorization: Bearer ds-test-token" -H "Content-Type: application/json" \
  -d '{"account_id":"acc-8171c752-...","stage":"activated"}'

# Advance activated → pro
curl -X POST http://localhost:18080/deals/deal-980768b3-.../advance \
  -H "Authorization: Bearer ds-test-token"

# Advance pro → teams
curl -X POST http://localhost:18080/deals/deal-980768b3-.../advance \
  -H "Authorization: Bearer ds-test-token"
```

Each advance auto-updates `mrr`, `probability`, and `value`. On `won`, updates the account's `mrr`, `arr`, and `lifetime_value` and fires Slack alert.

### 9.3. Pull the pipeline forecast

```bash
curl -H "Authorization: Bearer ds-test-token" \
  http://localhost:18080/pipeline/forecast
```

```json
{
  "total_deals":       1,
  "total_value":       348.0,
  "weighted_forecast": 261.0,
  "mrr":               21.75,
  "arr":               261.0,
  "by_persona":        "{\"enterprise-edge\":261.0}",
  "by_stream":         "{\"enterprise-subscription\":261.0}",
  "by_stage":          "{\"teams\":261.0}"
}
```

Math: `1 deal × $29/mo × 0.75 prob = $21.75 weighted MRR → $261 ARR`.

### 9.4. Register a bot for evolution + feed it signals

```bash
# Register (once)
curl -X POST http://localhost:18082/bots \
  -H "Authorization: Bearer $API_TOKEN" -H "Content-Type: application/json" \
  -d '{"id":"clow-team/telegram-summarizer","owner_email":"team@clow.dev"}'

# Ingest a signal (production would come from bot runtime EventBus)
curl -X POST http://localhost:18082/signals \
  -H "Authorization: Bearer $API_TOKEN" -H "Content-Type: application/json" \
  -d '{"bot_id":"clow-team/telegram-summarizer","signal_type":"conversation.ok","fitness_delta":0.15}'

# Once trajectories ≥ 100 AND ≥ 168h since last, cadence loop auto-triggers evolution.
# Or trigger manually:
curl -X POST http://localhost:18082/bots/clow-team%2Ftelegram-summarizer/evolve \
  -H "Authorization: Bearer $API_TOKEN"

# Public — no auth. Powers the marketplace widget.
curl http://localhost:18082/leaderboard
```

### 9.5. Scan a bot's endpoint

```bash
curl -X POST http://localhost:18081/scan \
  -H "Authorization: Bearer $API_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "target": "example-bot.fly.dev",
    "scan_types": ["recon", "web", "llm", "tls"]
  }'
```

Response: full `ScanResult` with `findings_json` + `severity_counts_json`. 0 critical = **Certified Secure Bot** badge on the marketplace.

---

## 10. API reference

Bearer auth on all mutating routes. `Authorization: Bearer $API_TOKEN`.

### 10.1. `gtm-engine` — https://ds-gtm-engine.fly.dev

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/health` | Liveness + row counts (no auth) |
| POST | `/accounts` | Ingest signup; scores + persona-classifies |
| GET  | `/accounts` | List sorted by score desc |
| POST | `/deals` | Create deal from `account_id` |
| POST | `/deals/{id}/advance` | Move deal to next stage |
| GET  | `/pipeline/forecast` | Weighted MRR/ARR by persona/stream/stage |
| GET  | `/audit` | Audit log tail |
| GET  | `/events` | KafCa bus recent events |
| GET  | `/signals` | Trajectory signals emitted |

### 10.2. `security-agent` — https://ds-security-agent.fly.dev

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/health` | Liveness (no auth) |
| POST | `/scan` | On-demand scan; types: `recon`, `web`, `llm`, `dependency`, `secret`, `tls` |
| GET  | `/findings` | All findings, newest first |
| GET  | `/ecosystem/report` | Compliance score across `SECURITY_TARGETS` |
| GET  | `/scan-history` | Scan history |
| GET  | `/audit` | Audit log |
| GET  | `/events` | KafCa bus |

### 10.3. `evo-metaclaw` — https://ds-evo-metaclaw.fly.dev

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/health` | Liveness (no auth) |
| GET  | `/leaderboard` | **Public** — top 10 evolving bots (marketplace widget source) |
| POST | `/bots` | Register bot for evolution |
| GET  | `/bots` | List bots by fitness desc |
| POST | `/bots/{id}/evolve` | Manually trigger evolution step |
| GET  | `/bots/{id}/history` | Evolution event log |
| POST | `/signals` | Ingest trajectory signal |
| GET  | `/signals` | List signals from `evo-metaclaw` |

### 10.4. Vercel Edge Functions

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/waitlist` | Waitlist ingest (tries `gtm-engine` → GitHub Issues → 200 always) |
| GET  | `/api/og` | Dynamic 1200×630 OG image; params `?title=` & `?subtitle=` |

### 10.5. SkillOpt worker

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/health` | Liveness |
| POST | `/train` | Run one SkillOpt training step; returns `gate_passed` + `gate_score_delta` + `next_version` |

---

## 11. Contributing

### 11.1. Add a new bot to the marketplace

1. `cp -r bots/telegram-summarizer bots/<your-bot>`
2. Edit `clow_bot.yaml` — name, description, pricing tier
3. Rewrite `skills/main.md` — behaviour, capabilities, guardrails, examples
4. Rewrite `eval/held_out.json` — 20+ cases with `reward_criteria`
5. Add your bot to `use_cases.html` if it belongs in the launch showcase
6. PR against this branch

### 11.2. Add a new service to the backend

1. `cd clow-agents/backend && cargo new --bin my-service`
2. Add `"my-service"` to the workspace `members` in `Cargo.toml`
3. Wire `shared::{auth,bus,config,db,notify}` in `main.rs`
4. Copy `gtm-engine/Dockerfile` + `fly.toml` as templates
5. Add to `scripts/deploy_fullstack.sh` and `scripts/smoke.sh`
6. `cargo check --workspace` must pass

### 11.3. Extend the GTM ICP scorer

Edit `clow-agents/backend/gtm-engine/src/main.rs`:
- `classify_persona()` — add domain / source / UA heuristics
- `score_account()` — adjust weights
- Add regression test cases to a new `held_out_leads.json` (not yet built — good first PR)

---

## 12. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `cargo check` fails on `sqlx::FromRow` | Ensure workspace `sqlx` has `"macros"` feature (already set in this branch). |
| Fly rejects app name | Names are globally unique. Change `PREFIX=` in `scripts/deploy_fullstack.sh`. |
| `/api/waitlist` returns 200 but no rows anywhere | Neither `GTM_ENGINE_URL` nor `GH_TOKEN` set. That's by design — landing localStorage + Plausible still catch the signal. Set one env to persist. |
| GitHub returns 401 on issue create | Fine-grained PAT expired or wrong repo scope. Regenerate with `Issues: read/write` on the exact `GH_REPO`. |
| Fly service cold-starts on first request | `auto_stop_machines = "stop"` in `fly.toml`. First hit takes ~2s; adjust `min_machines_running` if you need warm. |
| `evo-metaclaw` `/leaderboard` returns `[]` | No bots have completed an accepted evolution yet. Register a bot + feed ≥100 signals, then trigger evolve. |
| SkillOpt worker times out | Increase `subprocess.run(..., timeout=…)` in `scripts/skillopt_worker.py`. Default 3600s (1h). |
| Dashboard shows all services `down` | Bearer token mismatch. The `API_TOKEN` you passed to `deploy_fullstack.sh` must match what you type in the dashboard's token field. |

Full ops-side kill switches: [DEPLOY.md § 6](./DEPLOY.md#6-kill-switches-if-things-break).

---

## 13. Links

- **Live site:** [clow-tau.vercel.app](https://clow-tau.vercel.app)
- **X / Twitter:** [@XTech73781](https://twitter.com/XTech73781)
- **Clow repo:** [github.com/dnzengou/clow](https://github.com/dnzengou/clow)
- **This branch:** [github.com/dnzengou/SkillOpt · claude/clow-bots-marketing-gtm-p6nTm](https://github.com/dnzengou/SkillOpt/tree/claude/clow-bots-marketing-gtm-p6nTm)
- **SkillOpt paper:** [arXiv:2605.23904](https://arxiv.org/abs/2605.23904)
- **PicoClaw:** [github.com/sipeed/picoclaw](https://github.com/sipeed/picoclaw)
- **OpenClaw:** [openclaw.ai](https://openclaw.ai)

**Related docs in this repo:**
- [DEPLOY.md](./DEPLOY.md) — full deployment reference
- [EvoStack.md](./EvoStack.md) — name-space cheat sheet
- [EvoMetaClaw.md](./EvoMetaClaw.md) — self-evolving bots concept + arch
- [MARKETING.md](./MARKETING.md) — full ARM GTM strategy
- [Clow_GTM_Blueprint.md](./Clow_GTM_Blueprint.md) — living roadmap
- [clow-agents/README.md](./clow-agents/README.md) — backend-only reference
- [clow_bot_template.md](./clow_bot_template.md) — bot publisher template

---

*Clow manual v1.0 · MIT · [SkillOpt](https://arxiv.org/abs/2605.23904) × [PicoClaw](https://github.com/sipeed/picoclaw) · Powered by ARM (Adoption · Retention · Monetization) + RRSS (Robust · Reliable · Solid · Stable)*
