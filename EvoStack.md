# EvoStack — the Clow name-space cheat sheet
## v1.0 · June 2026

Every proper noun we use for Clow's technical & operational layers, what it means, and where it lives in the repo.

---

## THE STACK

```
                     ┌──────────────────────────┐
                     │      Clow marketplace    │
                     │   (bots · users · pubs)  │
                     └──────────┬───────────────┘
                                │
              ┌─────────────────┼───────────────────┐
              │                 │                   │
      ┌───────▼──────┐  ┌───────▼───────┐  ┌────────▼───────┐
      │   EvoForge   │  │   EvoMetaClaw │  │  Certified Sec │
      │  (build UX)  │  │ (self-improve)│  │  (bot audit)   │
      └───────┬──────┘  └───────┬───────┘  └────────┬───────┘
              │                 │                   │
              └────────┬────────┴───────────────────┘
                       │
              ┌────────▼─────────┐
              │    EvoSkillOpt   │  ← SkillOpt (arXiv:2605.23904) as a service
              │  scripts/train.py│
              └────────┬─────────┘
                       │
              ┌────────▼─────────┐
              │      KafCade     │  ← time-based orchestration on top of KafCa
              │  (nurture / evo  │
              │  eligibility)    │
              └────────┬─────────┘
                       │
              ┌────────▼─────────┐
              │       KafCa      │  ← broadcast bus + ring-buffer event log
              │ shared/src/bus.rs│
              └──────────────────┘

                    ↕ RRSS wraps all layers:
                    Robustify · Reliabilify · Solidify · Stabilize
```

---

## EACH NAME — WHAT IT IS, WHERE IT LIVES

### KafCa
**What:** In-process broadcast event bus with ring-buffer log. Named after the devflow token-efficiency mode (`Kf`) — the pun is intentional; it really is Kafka-lite in-process.

**Where:** `clow-agents/backend/shared/src/bus.rs`

**API:** `emit(Event)`, `subscribe() -> Receiver<Event>`, `recent(n) -> Vec<Event>`

**Topics emitted today:**
- `gtm.account.ingested` (by gtm-engine on waitlist signup)
- `evo.accepted` / `evo.rejected` (by evo-metaclaw after gate outcome)
- `security.scan.complete` (by security-agent)

### KafCade
**What:** The cadence layer on top of KafCa — scheduled tick loops that keep the system self-driving without any external cron.

**Where:** each service's `main.rs`:
- `gtm-engine::nurture_loop` — daily; flags dormant leads (>14d, no deal) to Slack
- `evo-metaclaw::eligibility_loop` — every 6h; scans all bots and triggers cadence-based evolution
- `security-agent::run_loop` — daily; re-scans all `SECURITY_TARGETS`

**Design:** each cadence loop is failure-isolated (own tokio task) and idempotent (each tick reads current state; missing a tick just delays work).

### EvoSkillOpt
**What:** SkillOpt (arXiv:2605.23904) packaged as an internal service. The training worker that turns real conversation trajectories into real skill-doc improvements.

**Where:**
- `scripts/skillopt_worker.py` — stdlib-only HTTP worker: `POST /train` → shells out to `scripts/train.py` → parses `history.json` for the gate delta
- `scripts/train.py` — SkillOpt's existing training entrypoint (unchanged)
- Bridge point: `evo-metaclaw::call_skillopt_worker` (Rust → HTTP → Python)

**Env:** set `SKILLOPT_WORKER_URL` + `SKILLOPT_WORKER_TOKEN` on evo-metaclaw. Unset = evo-metaclaw falls back to fitness-driven simulation (never blocks).

### EvoMetaClaw
**What:** The moat. Every bot in Clow can opt into self-evolution: KafCa signals + KafCade cadence + EvoSkillOpt training + a held-out eval gate. If the new skill beats the old one on the eval set, it ships. If not, it rolls back.

**Where:**
- `clow-agents/backend/evo-metaclaw/` — the Rust service
- `EvoMetaClaw.md` — the concept doc + commercial hooks
- Public endpoint: `GET /leaderboard` (top 10 evolving bots by fitness × accepted-count)

**User surface:** Pro tier ($9/mo) unlocks EvoMetaClaw for 1 bot; Teams for 5; Enterprise unlimited.

### EvoForge
**What:** The build-time UX for bot publishers. Everything they touch when they create, iterate, and publish a bot lives here — as opposed to EvoMetaClaw, which is the run-time story.

**Where:**
- `clow_bot_template.md` — the starter template (yaml + skill + eval)
- `bots/` — three concrete sample bots that publishers fork:
    - `bots/telegram-summarizer/` — free tier
    - `bots/discord-moderator/` — $3 subscription
    - `bots/slack-standup/` — $5 subscription
- Future: `clow` CLI (`clow init`, `clow publish`, `clow evolve --local`) — not yet built

**Commercial hook:** every published bot gets a marketplace slug + 70% revenue share. EvoForge is the *supply-side* flywheel; EvoMetaClaw is the *demand-side* differentiator.

### Certified Secure Bot
**What:** Free trust badge in the marketplace. A bot's endpoint is scanned by `security-agent`; if it returns 0 critical findings, it earns the ✨ badge for 30 days.

**Where:**
- `clow-agents/backend/security-agent/` — the scanner
- Scan types: `recon`, `web`, `llm` (prompt-injection red-team), `dependency`, `secret`, `tls`
- Marketplace surface: badge + `GET /findings?bot_id=…` for the public badge widget

**Why it matters:** free trust signal → 2× conversion for badged bots (publisher-facing incentive) → security-scanned catalog (buyer-facing trust).

### RRSS
**What:** The resilience discipline wrapped around every layer. Not a service — a rubric the codebase is measured against.

| Letter | Meaning | Where you'd look |
|--------|---------|------------------|
| **R**obustify | Timeouts on every outbound call, typed errors, rollback on evo failure | `shared/src/notify.rs` (10s timeouts), `evo-metaclaw::trigger_evolution` (never blocks caller) |
| **R**eliabilify | `/health` on every service, KafCa audit trail, KafCade heartbeats | every `main.rs` `/health` handler, `audit_logs` table |
| **S**olidify | Bearer auth on all mutating routes, SQLite migrations idempotent, unit-testable engine methods | `shared/src/auth.rs`, `shared/src/db.rs` |
| **S**tabilize | Independent Fly.io deploy per service, SQLite volume per service, in-memory rate limits with abuse ceilings | per-service `fly.toml` + `Dockerfile` |

Blueprint's RRSS section carries the same rubric to the *business* layer (LTV:CAC, forecast accuracy, brand monitoring).

---

## THE INITIALS TABLE (for pipeline commands)

| Alias | Skill | Full name | When you use it |
|-------|-------|-----------|-----------------|
| `Kf` | devflow | KafCa mode | Token-efficient session — verdict/code first, no preamble |
| `B` | devflow | Build | Ship the next roadmap item |
| `E` | devflow | Evaluate | Security / correctness / performance / quality audit |
| `Im` | devflow | Improve | Refactor without new features |
| `Bl` | devflow | Blueprint | Update `*_Blueprint.md` living doc |
| `P` | devflow | Push | Commit + push |
| `D` | devflow | Deploy | Ship to live target |
| `RRSS` | devflow / bizflow | Rb → Rl → So → St | Full resilience pipeline |
| `A / R / M` | bizflow | Acquire / Retain / Monetize | ARM funnel |
| `ARM` | bizflow | full sprint | A → R → M → Ar → Op → Sy → Rp → Sc |
| `CG` | bizflow | Continuous Growth | Ar → Op → Sy → Rp → Sc |

---

*EvoStack v1.0 · one-page onboarding for anyone new to the Clow codebase.*
