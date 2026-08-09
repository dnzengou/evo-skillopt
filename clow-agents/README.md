# clow-agents — GTM + Security + Evolution backend
## Rust · Axum · SQLite · Fly.io · KafCa bus

Three-service backend powering the Clow bots ecosystem operations layer.

| Service | Port | Purpose | Status |
|---------|------|---------|--------|
| `gtm-engine` | 8080 | Waitlist ingest, ICP scoring, deal pipeline, MRR forecast, dormant-lead nurture | **New** |
| `security-agent` | 8081 | Bot security scans → "Certified Secure" marketplace badge; recon/web/LLM red-team/dep/secret/TLS | Included |
| `evo-metaclaw` | 8082 | Trajectory signal ingest, per-bot fitness EMA, gate-triggered evolution, public leaderboard | **New** |

All three share `shared/` (models, auth, bus, db, notify, middleware) and persist to SQLite.

---

## Why this exists

The `clow_landing.html` waitlist form POSTs to `/api/waitlist` on Vercel (email storage). That's the front door. Everything after — scoring leads, moving them through Free→Pro→Teams→Enterprise, forecasting MRR, deciding which bots evolve when, deciding which bots earn the Certified Secure badge — is what this backend does.

**Wiring:**
```
clow_landing.html
   ↓ POST /api/waitlist (Vercel Edge)
   ↓ (optional) POST → gtm-engine:8080/accounts
         ↓ lead scored, deal created, MRR forecast updated
         ↓ trajectory_signal → shared SQLite

Bot in Clow registry
   ↓ POST → security-agent:8081/scan  → Certified Secure badge if 0 critical
   ↓ POST → evo-metaclaw:8082/signals → fitness EMA, triggers evolution
         ↓ evolution accepted/rejected → leaderboard (public)
```

---

## Quick start (local)

```bash
cd clow-agents/backend
cp .env.example .env
# Edit .env; at minimum set API_TOKEN

# Run all three (each in its own terminal)
cargo run -p gtm-engine     # :8080
cargo run -p security-agent # PORT=8081 cargo run -p security-agent
cargo run -p evo-metaclaw   # PORT=8082 cargo run -p evo-metaclaw

# Health checks (no auth)
curl localhost:8080/health
curl localhost:8081/health
curl localhost:8082/health
```

## Deploy (Fly.io)

Each service has its own `fly.toml` and `Dockerfile`. Deploy independently:

```bash
cd clow-agents/backend/gtm-engine     && fly deploy
cd clow-agents/backend/security-agent && fly deploy
cd clow-agents/backend/evo-metaclaw   && fly deploy
```

---

## GTM Engine — endpoints

Bearer auth (except `/health`). Token from `API_TOKEN` env.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness + row counts |
| POST | `/accounts` | Ingest waitlist signup; auto-scores + persona-classifies |
| GET | `/accounts` | List, sorted by score desc |
| POST | `/deals` | Create deal from account_id |
| POST | `/deals/{id}/advance` | Move deal to next stage (auto-updates MRR + probability) |
| GET | `/pipeline/forecast` | Weighted MRR/ARR by persona, revenue stream, stage |
| GET | `/audit` | Audit log tail |
| GET | `/events` | KafCa bus recent events |
| GET | `/signals` | Trajectory signals emitted |

**ICP scoring:** email domain (free-mail vs corporate) + source (github/twitter/PH/HN/discord) + stated plan interest + persona bonus. Range: 0–100. Hot-lead alert to Slack fires at persona=`enterprise-edge` AND score≥70.

**Personas** (from MARKETING.md): `edge-builder`, `automation-dev`, `enterprise-edge`.

## Security Agent — endpoints

Same auth model. Runs daily scans on `SECURITY_TARGETS`.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| POST | `/scan` | On-demand scan (recon/web/llm/dependency/secret/tls) — rate-limited |
| GET | `/findings` | All findings ordered by ts desc |
| GET | `/ecosystem/report` | Compliance score across all targets |
| GET | `/scan-history` | Scan history |

**Commercial hook:** bot in marketplace submits URL → security-agent scans → 0 critical findings unlocks the **✨ Certified Secure Bot** badge. Users filter for it. Publishers earn 2× conversion.

## EvoMetaClaw — endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/leaderboard` | **Public** — top 10 evolving bots (marketplace widget source) |
| POST | `/bots` | Register bot for evolution |
| GET | `/bots` | List bots by fitness desc |
| POST | `/bots/{id}/evolve` | Manually trigger evolution step |
| GET | `/bots/{id}/history` | Evolution event log |
| POST | `/signals` | Ingest trajectory signal (bot_id, signal_type, fitness_delta) |

**Fitness model:** exponential moving average (α=0.1) over trajectory `fitness_delta` values in [-1, 1]. Rolls forward permanently until gate rejects.

**Evolution trigger:** conversation count ≥ `EVOLUTION_TRAJECTORY_THRESHOLD` (100) AND ≥ `EVOLUTION_MIN_INTERVAL_HOURS` (168h = weekly) since last evolution.

**Gate:** simulated score delta ≥ `GATE_MIN_IMPROVEMENT` (5%). Real integration point: replace `trigger_evolution`'s simulation block with `POST http://skillopt-worker/train` calling `scripts/train.py` from the SkillOpt repo. This is the SkillOpt × Clow bridge.

---

## Shared library

All three services depend on `shared/`:
- `models.rs` — Account, Deal, Finding, ScanResult, AuditLog, TrajectorySignal
- `bus.rs` — **KafCa**: broadcast::channel + ring-buffer log (the token-efficiency mode's namesake)
- `auth.rs` — Bearer token middleware (dev-token bypass for local)
- `db.rs` — SQLite init + migrations (idempotent CREATE IF NOT EXISTS)
- `audit.rs` — Immutable append-only audit log
- `notify.rs` — Slack + Resend email + PagerDuty
- `middleware.rs` — CORS, request logging, graceful shutdown
- `config.rs` — Env-driven config (`API_TOKEN`, `GTM_TARGETS`, `SECURITY_TARGETS`, `SLACK_WEBHOOK`, `RESEND_KEY`, `PAGERDUTY_KEY`, `LLM_API_KEY`, `LLM_BASE_URL`, `DATABASE_URL`, `CORS_ORIGIN`, `RATE_LIMIT_PER_MINUTE`)

---

## RRSS status

| Dimension | Status |
|-----------|--------|
| Robust | Graceful shutdown; timeouts on all outbound HTTP; typed errors; storage failures never leak to client |
| Reliable | Health endpoints; audit log; KafCa bus event trail; daily nurture + eligibility ticks |
| Solid | Unit-testable engine methods; SQLite migrations idempotent; bearer auth on all mutating routes |
| Stable | Per-service Fly.io deploy; independent scaling; SQLite volume per service |

## Missing / follow-ups

- [ ] Cross-service SQLite: currently each service has its own file. Move to shared Postgres for real cross-service queries (evo needs to read gtm signals). Kept SQLite for MVP simplicity.
- [ ] Real SkillOpt bridge: replace simulated gate in `evo-metaclaw::trigger_evolution` with `reqwest` call to a SkillOpt Python worker.
- [ ] `governor_tower` dep name — verify against latest crates.io (name was `tower_governor` at one point).
- [ ] Dashboard UI — the endpoints are ready; needs a React/Svelte dashboard consuming `/pipeline/forecast`, `/leaderboard`, `/findings`.
